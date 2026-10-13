"""Win32 launcher for the CPython embedded portable build. No Tk dependency."""
import sys,os,threading,webbrowser,ctypes,time,json,sqlite3
from ctypes import wintypes
import app

def main(smoke=False):
    if sys.platform!='win32':raise RuntimeError('Windows原生入口仅在Windows运行')
    user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    LRESULT=ctypes.c_ssize_t;WNDPROC=ctypes.WINFUNCTYPE(LRESULT,wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM)
    class WNDCLASS(ctypes.Structure):
        _fields_=[('style',wintypes.UINT),('lpfnWndProc',WNDPROC),('cbClsExtra',ctypes.c_int),('cbWndExtra',ctypes.c_int),('hInstance',wintypes.HINSTANCE),('hIcon',wintypes.HICON),('hCursor',wintypes.HANDLE),('hbrBackground',wintypes.HBRUSH),('lpszMenuName',wintypes.LPCWSTR),('lpszClassName',wintypes.LPCWSTR)]
    user.DefWindowProcW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM];user.DefWindowProcW.restype=LRESULT
    user.CreateWindowExW.argtypes=[wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HWND,wintypes.HMENU,wintypes.HINSTANCE,ctypes.c_void_p];user.CreateWindowExW.restype=wintypes.HWND
    kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];kernel.GetModuleHandleW.restype=wintypes.HMODULE
    user.RegisterClassW.argtypes=[ctypes.POINTER(WNDCLASS)];user.RegisterClassW.restype=wintypes.ATOM
    user.DestroyWindow.argtypes=[wintypes.HWND];user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
    @WNDPROC
    def proc(hwnd,msg,wparam,lparam):
        if msg==0x111 and (wparam&0xffff)==101:webbrowser.open('http://127.0.0.1:8891');return 0
        if msg==2:user.PostQuitMessage(0);return 0
        return user.DefWindowProcW(hwnd,msg,wparam,lparam)
    instance=kernel.GetModuleHandleW(None);wc=WNDCLASS(0,proc,0,0,instance,None,None,ctypes.c_void_p(6),None,'ApplicationAdvisorWindow')
    if not user.RegisterClassW(ctypes.byref(wc)):raise ctypes.WinError(ctypes.get_last_error())
    hwnd=user.CreateWindowExW(0,wc.lpszClassName,'申报参谋 桌面客户端',0x00CF0000,100,100,580,310,None,None,instance,None)
    if not hwnd:raise ctypes.WinError(ctypes.get_last_error())
    user.CreateWindowExW(0,'STATIC','申报参谋\n\n政策解析  资格核验  申报书草稿\n\n保持此窗口打开，本地政策提醒每分钟检查一次。',0x50000000,28,22,520,140,hwnd,None,instance,None)
    user.CreateWindowExW(0,'BUTTON','打开申报工作台',0x50000000,28,175,250,42,hwnd,ctypes.c_void_p(101),instance,None)
    if smoke:
        user.DestroyWindow(hwnd);print('WIN32_WINDOW_SMOKE_OK');return
    threading.Thread(target=app.serve,daemon=True).start();user.ShowWindow(hwnd,1)
    def alerts():
        seen=set()
        while True:
            try:
                with sqlite3.connect(app.DB) as db:rows=db.execute('SELECT id,data FROM alerts').fetchall()
                for id,data in rows:
                    if id in seen:continue
                    seen.add(id);a=json.loads(data)
                    if not a.get('read'):user.MessageBoxW(None,a['project']+'\n'+a['label']+'\n'+a['date'],'政策截止提醒',0x40)
            except Exception:pass
            time.sleep(60)
    threading.Thread(target=alerts,daemon=True).start()
    threading.Timer(1,lambda:webbrowser.open('http://127.0.0.1:8891')).start()
    msg=wintypes.MSG()
    while user.GetMessageW(ctypes.byref(msg),None,0,0)>0:user.TranslateMessage(ctypes.byref(msg));user.DispatchMessageW(ctypes.byref(msg))
if __name__=='__main__':main('--smoke' in sys.argv)
