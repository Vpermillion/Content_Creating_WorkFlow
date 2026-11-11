"""Local Ifverse controls for OAuth, reviewed schedules and publishing status."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

import publishing_dashboard as publishing


def build(root):
    root.title('Ifverse Publishing')
    root.geometry('890x550')
    root.minsize(680, 430)
    panel = ttk.Frame(root, padding=22)
    panel.pack(fill='both', expand=True)
    ttk.Label(panel, text='Ifverse Publishing', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
    ttk.Label(panel, text='Verify channels, queue reviewed schedules and track each destination.').pack(anchor='w', pady=(4, 18))

    toolbar = ttk.Frame(panel)
    toolbar.pack(fill='x')
    aliases = tuple(sorted(publishing.accounts.registry(publishing.ROOT)))
    account = tk.StringVar(value=aliases[0] if aliases else '')
    ttk.Label(toolbar, text='Publishing account').pack(side='left', padx=(0, 5))
    destination = ttk.Combobox(toolbar, state='readonly', values=aliases, textvariable=account, width=34)
    destination.pack(side='left', padx=(0, 8))
    actions = ttk.Frame(panel)
    actions.pack(fill='x', pady=(10, 0))
    status = tk.StringVar(value='Ready')
    ttk.Label(panel, textvariable=status).pack(anchor='w', pady=(12, 6))
    console = tk.Text(panel, height=18, wrap='word', state='disabled', font=('Consolas', 10))
    console.pack(fill='both', expand=True)
    executor = ThreadPoolExecutor(max_workers=1)
    buttons = []

    def show(text):
        console.configure(state='normal')
        console.delete('1.0', 'end')
        console.insert('end', text)
        console.configure(state='disabled')

    def run(args, finished=None):
        for button in buttons:
            button.state(['disabled'])
        status.set('Working…')
        future = executor.submit(subprocess.run, [sys.executable, str(Path(publishing.__file__)), *args],
                                 capture_output=True, text=True, encoding='utf-8', errors='replace',
                                 env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})

        def receive():
            if not future.done():
                root.after(100, receive)
                return
            for button in buttons:
                button.state(['!disabled'])
            try:
                result = future.result()
                if result.returncode:
                    status.set('Needs attention')
                    show((result.stdout + result.stderr).strip())
                else:
                    status.set('Ready')
                    if finished is None:
                        show((result.stdout + result.stderr).strip())
                    else:
                        finished(result.stdout.strip(), result.stderr.strip())
            except (OSError, ValueError):
                status.set('Needs attention')
                show('The command could not finish. Check local configuration and the publishing queue.')

        root.after(100, receive)

    def schedule():
        path = filedialog.askopenfilename(title='Choose the reviewed publishing manifest',
                                          filetypes=[('JSON manifest', '*.json')], parent=root)
        if not path:
            return
        approved = messagebox.askyesno('Submit reviewed schedule',
            'Queue these reviewed destinations? The repository worker will publish supported jobs when due.',
            parent=root)
        if approved:
            run(['queue', path])

    def open_dashboard(path, warnings):
        webbrowser.open(Path(path).as_uri())
        show(warnings or 'Opened the dashboard with the latest provider status.')

    for label, action in (
        ('Check account', lambda: run(['verify-account', account.get()])),
        ('Queue reviewed manifest', schedule),
        ('Run due jobs', lambda: run(['run-due'])),
        ('Open live status', lambda: run(['dashboard', '--refresh'], open_dashboard)),
        ('Open local queue', lambda: run(['dashboard'], open_dashboard)),
    ):
        button = ttk.Button(actions, text=label, command=action)
        button.pack(side='left', padx=(0, 7))
        buttons.append(button)

    def close():
        executor.shutdown(wait=False)
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    show('Register platform accounts in channels/publishing-accounts.json and configure their grants privately. Select an account to check access.\n\n'
         'Queue a reviewed JSON manifest to schedule a video. Use Run due jobs or start the watch worker.')


if __name__ == '__main__':
    window = tk.Tk()
    build(window)
    window.mainloop()
