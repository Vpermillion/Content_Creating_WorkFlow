"""Local Ifverse controls for OAuth, reviewed schedules and publishing status."""
from concurrent.futures import ThreadPoolExecutor
import json
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
    ttk.Label(panel, text='Connect your channels, submit a reviewed schedule and track each destination.').pack(anchor='w', pady=(4, 18))

    toolbar = ttk.Frame(panel)
    toolbar.pack(fill='x')
    platform = tk.StringVar(value=publishing.PLATFORMS[0])
    destination = ttk.Combobox(toolbar, state='readonly', values=publishing.PLATFORMS, textvariable=platform, width=13)
    destination.pack(side='left', padx=(0, 8))
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

    def open_consent(url, _warnings):
        if publishing.https(url):
            webbrowser.open(url)
            show('Complete provider consent in Chrome, then select Check accounts.')
        else:
            show('No valid provider consent URL was returned.')

    def accounts(text, _warnings):
        rows = json.loads(text)
        lines = ['Connected accounts for the configured publishing profile', '']
        for destination in publishing.PLATFORMS:
            matches = [row for row in rows if row['platform'] == destination]
            label = ', '.join(f"{row['username']}  •  {row['_id']}" for row in matches)
            lines.append(f'{destination.title():12} {label or "No active connection"}')
        show('\n'.join(lines))

    def schedule():
        path = filedialog.askopenfilename(title='Choose the reviewed publishing manifest',
                                          filetypes=[('JSON manifest', '*.json')], parent=root)
        if not path:
            return
        approved = messagebox.askyesno('Submit reviewed schedule',
            'Send the reviewed videos and captions in this manifest to Zernio for scheduled publication?',
            parent=root)
        if approved:
            run(['schedule', path, '--submit'])

    def open_dashboard(path, warnings):
        webbrowser.open(Path(path).as_uri())
        show(warnings or 'Opened the dashboard with the latest provider status.')

    for label, action in (
        ('Connect', lambda: run(['connect', platform.get()], open_consent)),
        ('Check accounts', lambda: run(['accounts'], accounts)),
        ('Submit schedule', schedule),
        ('Open live status', lambda: run(['dashboard', '--refresh'], open_dashboard)),
        ('Open local queue', lambda: run(['dashboard'], open_dashboard)),
    ):
        button = ttk.Button(toolbar, text=label, command=action)
        button.pack(side='left', padx=(0, 7))
        buttons.append(button)

    def close():
        executor.shutdown(wait=False)
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    show('Choose a destination and select Connect. Complete the provider consent screen to grant access.\n\n'
         'Submit a reviewed JSON manifest to schedule a video. Open the local queue any time.')


if __name__ == '__main__':
    window = tk.Tk()
    build(window)
    window.mainloop()
