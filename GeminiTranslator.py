import customtkinter as ctk
import configparser
import threading
import time
import keyboard
import pyperclip
import os
from google import genai

# --- 配置初始化 (.ini 格式) ---
CONFIG_FILE = 'config.ini'
config = configparser.ConfigParser()

def load_config():
    if not os.path.exists(CONFIG_FILE):
        config['SETTINGS'] = {
            'api_key': '',
            'shortcut': 'ctrl+c+c',
            'topmost': 'True',
            'model': 'gemini-2.5-flash' # 新增：默认模型设置
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    else:
        config.read(CONFIG_FILE, encoding='utf-8')
        # 向下兼容：如果旧的配置文件里没有 topmost 或 model 选项，则自动补全
        if 'topmost' not in config['SETTINGS']:
            config['SETTINGS']['topmost'] = 'True'
        if 'model' not in config['SETTINGS']:
            config['SETTINGS']['model'] = 'gemini-2.5-flash'

def save_config(api_key, shortcut, topmost, model):
    config['SETTINGS']['api_key'] = api_key
    config['SETTINGS']['shortcut'] = shortcut
    config['SETTINGS']['topmost'] = str(topmost)
    config['SETTINGS']['model'] = model # 保存选择的模型
    with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

load_config()

# --- 主界面应用 ---
class TranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gemini 翻译工具") 
        self.geometry("600x450")
        
        # 读取配置并应用初始的置顶状态
        is_topmost = config['SETTINGS'].getboolean('topmost', fallback=True)
        self.attributes("-topmost", is_topmost) 
        
        # 布局配置
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. 上半部分：输入区域 (包含输入框和右侧按钮组)
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="nsew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_rowconfigure(0, weight=1)

        self.input_textbox = ctk.CTkTextbox(self.input_frame, font=("Microsoft YaHei", 14))
        self.input_textbox.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        # 绑定回车键直接翻译 (Shift+Enter 换行)
        self.input_textbox.bind("<Return>", self.on_enter_pressed)

        # 按钮组框架，用于上下排列翻译和清空按钮
        self.button_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.button_frame.grid(row=0, column=1, sticky="ns")
        self.button_frame.grid_rowconfigure(0, weight=1)
        self.button_frame.grid_rowconfigure(1, weight=1)

        # 翻译按钮
        self.translate_btn = ctk.CTkButton(self.button_frame, text="翻 译\n(Enter)", width=80, 
                                           command=self.perform_translation)
        self.translate_btn.grid(row=0, column=0, sticky="s", pady=(0, 5))

        # 清空按钮
        self.clear_btn = ctk.CTkButton(self.button_frame, text="清 空", width=80, 
                                       fg_color="gray50", hover_color="gray40", 
                                       command=self.clear_text)
        self.clear_btn.grid(row=1, column=0, sticky="n", pady=(5, 0))

        # 2. 下半部分：输出区域
        self.output_textbox = ctk.CTkTextbox(self, font=("Microsoft YaHei", 14), state="disabled", fg_color=("gray90", "gray16"))
        self.output_textbox.grid(row=1, column=0, padx=15, pady=(5, 10), sticky="nsew")

        # 3. 左下角：设置按钮
        self.settings_btn = ctk.CTkButton(self, text="⚙ 设置", width=60, height=24, 
                                          fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
                                          command=self.open_settings)
        self.settings_btn.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="w")

        # 启动全局快捷键监听线程
        self.setup_global_hotkey()

    def on_enter_pressed(self, event):
        # 拦截默认的回车换行事件，执行翻译
        self.perform_translation()
        return "break"

    def clear_text(self):
        # 清空输入框
        self.input_textbox.delete("1.0", "end")
        # 清空输出框
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", "end")
        self.output_textbox.configure(state="disabled")

    def perform_translation(self, text_to_translate=None):
        # 如果没有传入文本，则从输入框获取
        if not text_to_translate:
            text_to_translate = self.input_textbox.get("1.0", "end-1c").strip()
            
        if not text_to_translate:
            return

        # UI 状态更新
        self.translate_btn.configure(text="翻译中...", state="disabled")
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", "end")
        
        # 获取当前选择的模型名称并显示在提示信息中
        selected_model = config['SETTINGS'].get('model', 'gemini-2.5-flash')
        self.output_textbox.insert("end", f"正在调用 {selected_model} 进行翻译...\n")
        self.output_textbox.configure(state="disabled")
        self.update()

        # --- Gemini API 调用 ---
        api_key = config['SETTINGS'].get('api_key', '')
        
        if not api_key.strip():
            result_text = "⚠️ 请先点击左下角【设置】配置你的 Gemini API Key！"
        else:
            try:
                # 初始化新版客户端
                client = genai.Client(api_key=api_key)
                # 调用生成接口，动态传入配置中的模型
                response = client.models.generate_content(
                    model=selected_model, 
                    contents=f"请将以下内容翻译为中文（如果是中文则直接翻译为英文），只需要输出翻译后的结果，不要多余的解释：\n{text_to_translate}"
                )
                result_text = response.text
                
            except Exception as e:
                result_text = f"❌ 翻译出错，请检查网络或 API Key 是否正确。\n错误信息: {e}"

        # 显示结果并写入剪贴板
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", "end")
        self.output_textbox.insert("end", result_text)
        self.output_textbox.configure(state="disabled")
        
        pyperclip.copy(result_text) # 直接复制到剪贴板
        
        self.translate_btn.configure(text="已复制\n(Enter)", state="normal")
        self.after(2000, lambda: self.translate_btn.configure(text="翻 译\n(Enter)")) # 2秒后按钮文字恢复

    def open_settings(self):
        # 设置弹窗
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("设置")
        # 增加高度以容纳模型选择框
        settings_window.geometry("400x380")
        settings_window.attributes("-topmost", True)
        settings_window.grab_set() # 模态窗口

        # 1. API Key 输入
        ctk.CTkLabel(settings_window, text="Gemini API Key:").pack(pady=(10, 5), padx=20, anchor="w")
        api_entry = ctk.CTkEntry(settings_window, width=360)
        api_entry.pack(padx=20)
        api_entry.insert(0, config['SETTINGS'].get('api_key', ''))

        # 2. 模型选择下拉框 (新增)
        ctk.CTkLabel(settings_window, text="模型选择 (Model):").pack(pady=(15, 5), padx=20, anchor="w")
        # 预设几个常用的 Gemini 模型供选择
        available_models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        model_var = ctk.StringVar(value=config['SETTINGS'].get('model', 'gemini-2.5-flash'))
        model_dropdown = ctk.CTkOptionMenu(settings_window, values=available_models, variable=model_var, width=360)
        model_dropdown.pack(padx=20)

        # 3. 快捷键说明
        ctk.CTkLabel(settings_window, text="快捷键 (如 ctrl+c+c, 暂仅支持说明展示):").pack(pady=(15, 5), padx=20, anchor="w")
        shortcut_entry = ctk.CTkEntry(settings_window, width=360)
        shortcut_entry.pack(padx=20)
        shortcut_entry.insert(0, config['SETTINGS'].get('shortcut', 'ctrl+c+c'))

        # 4. 窗口置顶复选框
        current_topmost = config['SETTINGS'].getboolean('topmost', fallback=True)
        topmost_var = ctk.BooleanVar(value=current_topmost)
        topmost_checkbox = ctk.CTkCheckBox(settings_window, text="📌 窗口始终保持在最前 (置顶)", 
                                           variable=topmost_var)
        topmost_checkbox.pack(pady=(15, 5), padx=20, anchor="w")

        def save_and_close():
            # 保存所有设置到 .ini 文件，包含选择的模型
            save_config(api_entry.get(), shortcut_entry.get(), topmost_var.get(), model_var.get())
            # 即时生效：立刻改变主窗口的置顶状态
            self.attributes("-topmost", topmost_var.get())
            settings_window.destroy()

        ctk.CTkButton(settings_window, text="保存", command=save_and_close).pack(pady=(15, 5))
        
        # 版本号更新为 v1.0.002
        ctk.CTkLabel(settings_window, text="v1.0.002", text_color="gray50", font=("Microsoft YaHei", 10)).pack(side="bottom", pady=5)

    def setup_global_hotkey(self):
        # 使用 keyboard 库在后台线程监听双击 Ctrl+C
        self.last_c_time = 0
        
        def on_c_press(e):
            if keyboard.is_pressed('ctrl'):
                current_time = time.time()
                # 检查两次按下 'c' 的时间差是否小于 0.5 秒
                if current_time - self.last_c_time < 0.5:
                    self.last_c_time = 0 # 重置
                    # 触发翻译逻辑 (需要通过 after 确保在主线程更新 UI)
                    self.after(100, self.trigger_from_clipboard)
                else:
                    self.last_c_time = current_time

        keyboard.on_press_key('c', on_c_press)

    def trigger_from_clipboard(self):
        # 稍微延迟以确保系统的 Ctrl+C 已经把内容放进剪贴板
        time.sleep(0.1)
        clipboard_text = pyperclip.paste()
        if clipboard_text:
            # 唤醒窗口
            self.deiconify()
            
            # 如果当前没有置顶，唤醒时将窗口拉到最前面获取焦点
            if not config['SETTINGS'].getboolean('topmost', fallback=True):
                self.focus_force()
                
            # 填充输入框并翻译
            self.input_textbox.delete("1.0", "end")
            self.input_textbox.insert("end", clipboard_text)
            self.perform_translation(clipboard_text)

if __name__ == "__main__":
    # 设置主题风格
    ctk.set_appearance_mode("System")  # 跟随系统深色/浅色
    ctk.set_default_color_theme("blue") 
    
    app = TranslatorApp()
    app.mainloop()