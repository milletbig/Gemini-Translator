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
            'model': 'gemini-2.5-flash'
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    else:
        config.read(CONFIG_FILE, encoding='utf-8')
        if 'topmost' not in config['SETTINGS']:
            config['SETTINGS']['topmost'] = 'True'
        if 'model' not in config['SETTINGS']:
            config['SETTINGS']['model'] = 'gemini-2.5-flash'

def save_config(api_key, shortcut, topmost, model):
    config['SETTINGS']['api_key'] = api_key
    config['SETTINGS']['shortcut'] = shortcut
    config['SETTINGS']['topmost'] = str(topmost)
    config['SETTINGS']['model'] = model
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

        # 1. 上半部分：输入区域
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="nsew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_rowconfigure(0, weight=1)

        self.input_textbox = ctk.CTkTextbox(self.input_frame, font=("Microsoft YaHei", 14))
        self.input_textbox.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        self.input_textbox.bind("<Return>", self.on_enter_pressed)

        # 按钮组框架
        self.button_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.button_frame.grid(row=0, column=1, sticky="ns")
        self.button_frame.grid_rowconfigure(0, weight=1)
        self.button_frame.grid_rowconfigure(1, weight=1)

        self.translate_btn = ctk.CTkButton(self.button_frame, text="翻 译\n(Enter)", width=80, 
                                           command=self.perform_translation)
        self.translate_btn.grid(row=0, column=0, sticky="s", pady=(0, 5))

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
        self.perform_translation()
        return "break"

    def clear_text(self):
        self.input_textbox.delete("1.0", "end")
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", "end")
        self.output_textbox.configure(state="disabled")

    def perform_translation(self, text_to_translate=None):
        if not text_to_translate:
            text_to_translate = self.input_textbox.get("1.0", "end-1c").strip()
            
        if not text_to_translate:
            return

        self.translate_btn.configure(text="翻译中...", state="disabled")
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", "end")
        
        selected_model = config['SETTINGS'].get('model', 'gemini-2.5-flash')
        self.output_textbox.insert("end", f"正在调用 {selected_model} 进行翻译...\n")
        self.output_textbox.configure(state="disabled")
        self.update()

        api_key = config['SETTINGS'].get('api_key', '')
        
        if not api_key.strip():
            result_text = "⚠️ 请先点击左下角【设置】配置你的 Gemini API Key！"
        else:
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=selected_model, 
                    contents=f"请将以下内容翻译为中文（如果是中文则直接翻译为英文），只需要输出翻译后的结果，不要多余的解释：\n{text_to_translate}"
                )
                result_text = response.text
                
            except Exception as e:
                result_text = f"❌ 翻译出错，请检查网络或 API Key 是否正确。\n错误信息: {e}"

        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", "end")
        self.output_textbox.insert("end", result_text)
        self.output_textbox.configure(state="disabled")
        
        pyperclip.copy(result_text)
        
        self.translate_btn.configure(text="已复制\n(Enter)", state="normal")
        self.after(2000, lambda: self.translate_btn.configure(text="翻 译\n(Enter)"))

    def open_settings(self):
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("设置")
        settings_window.geometry("400x380")
        settings_window.attributes("-topmost", True)
        settings_window.grab_set() 

        # 1. API Key 输入
        ctk.CTkLabel(settings_window, text="Gemini API Key:").pack(pady=(10, 5), padx=20, anchor="w")
        api_entry = ctk.CTkEntry(settings_window, width=360)
        api_entry.pack(padx=20)
        api_entry.insert(0, config['SETTINGS'].get('api_key', ''))

        # 2. 模型选择及实时抓取
        model_label_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
        model_label_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(model_label_frame, text="模型选择 (Model):").pack(side="left")
        
        # 初始默认列表 (合并已保存的配置模型)
        default_models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash"]
        saved_model = config['SETTINGS'].get('model', 'gemini-2.5-flash')
        if saved_model not in default_models:
            default_models.insert(0, saved_model)
            
        model_var = ctk.StringVar(value=saved_model)
        model_dropdown = ctk.CTkOptionMenu(settings_window, values=default_models, variable=model_var, width=360)
        model_dropdown.pack(padx=20)

        # 实时抓取模型的逻辑
        def fetch_models():
            refresh_btn.configure(text="获取中...", state="disabled")
            current_key = api_entry.get().strip()
            if not current_key:
                refresh_btn.configure(text="⚠️ 请先输入 Key", text_color="red")
                settings_window.after(2000, lambda: refresh_btn.configure(text="🔄 实时获取", text_color=("gray10", "gray90"), state="normal"))
                return
                
            try:
                client = genai.Client(api_key=current_key)
                fetched_models = []
                for m in client.models.list():
                    # 剥离前缀并过滤掉纯向量或问答模型，保留支持文本生成的 gemini 模型
                    name = m.name.replace('models/', '') if m.name.startswith('models/') else m.name
                    if 'gemini' in name.lower() and 'embedding' not in name.lower() and 'aqa' not in name.lower():
                        fetched_models.append(name)
                
                if fetched_models:
                    # 去重并降序排序 (让新模型排在前面)
                    fetched_models = sorted(list(set(fetched_models)), reverse=True)
                    model_dropdown.configure(values=fetched_models)
                    if model_var.get() not in fetched_models:
                        model_var.set(fetched_models[0])
                    refresh_btn.configure(text="✅ 获取成功", text_color="green")
                else:
                    refresh_btn.configure(text="❌ 未找到模型", text_color="red")
            except Exception as e:
                refresh_btn.configure(text="❌ 获取失败", text_color="red")
                print(f"获取模型失败: {e}")
                
            # 2秒后恢复按钮状态
            settings_window.after(2000, lambda: refresh_btn.configure(text="🔄 实时获取", text_color=("gray10", "gray90"), state="normal"))

        def fetch_models_thread():
            # 将网络请求放入子线程，防止界面卡死
            threading.Thread(target=fetch_models, daemon=True).start()

        refresh_btn = ctk.CTkButton(model_label_frame, text="🔄 实时获取", width=80, height=24, 
                                    fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
                                    command=fetch_models_thread)
        refresh_btn.pack(side="right")

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
            save_config(api_entry.get(), shortcut_entry.get(), topmost_var.get(), model_var.get())
            self.attributes("-topmost", topmost_var.get())
            settings_window.destroy()

        ctk.CTkButton(settings_window, text="保存", command=save_and_close).pack(pady=(15, 5))
        
        # 版本号更新为 v1.0.003
        ctk.CTkLabel(settings_window, text="v1.0.003", text_color="gray50", font=("Microsoft YaHei", 10)).pack(side="bottom", pady=5)

    def setup_global_hotkey(self):
        self.last_c_time = 0
        
        def on_c_press(e):
            if keyboard.is_pressed('ctrl'):
                current_time = time.time()
                if current_time - self.last_c_time < 0.5:
                    self.last_c_time = 0 
                    self.after(100, self.trigger_from_clipboard)
                else:
                    self.last_c_time = current_time

        keyboard.on_press_key('c', on_c_press)

    def trigger_from_clipboard(self):
        time.sleep(0.1)
        clipboard_text = pyperclip.paste()
        if clipboard_text:
            self.deiconify()
            if not config['SETTINGS'].getboolean('topmost', fallback=True):
                self.focus_force()
                
            self.input_textbox.delete("1.0", "end")
            self.input_textbox.insert("end", clipboard_text)
            self.perform_translation(clipboard_text)

if __name__ == "__main__":
    ctk.set_appearance_mode("System")  
    ctk.set_default_color_theme("blue") 
    
    app = TranslatorApp()
    app.mainloop()