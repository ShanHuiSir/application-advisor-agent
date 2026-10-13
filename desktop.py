"""Windows desktop launcher; the standard-library Tk window controls service lifetime."""
import os,sys,threading,webbrowser,tkinter as tk
from pathlib import Path
import app

def main():
    window=tk.Tk();window.title('申报参谋 桌面客户端');window.geometry('560x330');window.configure(bg='#f0f3f7')
    threading.Thread(target=app.serve,daemon=True).start()
    tk.Label(window,text='申报参谋',font=('Microsoft YaHei',26,'bold'),bg='#f0f3f7',fg='#153d6a').pack(pady=(30,14))
    tk.Label(window,text='政策解析 · 资格核验 · 申报书草稿\n保持此窗口打开，本地政策提醒每分钟检查一次。',font=('Microsoft YaHei',11),bg='#f0f3f7').pack()
    tk.Button(window,text='打开申报工作台',font=('Microsoft YaHei',12),command=lambda:webbrowser.open('http://127.0.0.1:8891')).pack(pady=20)
    status=tk.Label(window,text='正在启动本地服务',bg='#f0f3f7',wraplength=510);status.pack()
    seen=set()
    def poll():
        import sqlite3,json
        try:
            with sqlite3.connect(app.DB) as db:rows=db.execute('SELECT id,data FROM alerts').fetchall()
            pending=[(i,json.loads(d)) for i,d in rows if i not in seen]
            for i,d in pending:
                seen.add(i)
                if not d.get('read'):
                    t=tk.Toplevel(window);t.title('政策截止提醒');tk.Label(t,text=d['project']+'\n'+d['label']+'\n'+d['date']+'\n请及时准备与提交材料',padx=25,pady=25).pack()
            status.configure(text='本地服务已启动；提醒状态每分钟更新。')
        except Exception:status.configure(text='服务启动中或数据库未就绪。')
        window.after(60000,poll)
    window.after(1000,poll);window.after(1000,lambda:webbrowser.open('http://127.0.0.1:8891'));window.mainloop()
if __name__=='__main__':main()
