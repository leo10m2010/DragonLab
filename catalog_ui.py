"""Searchable consultation of actual catalogue records; never changes game state."""
import tkinter as tk
from tkinter import ttk
from game_profiles import registered_profiles, get_profile
from mobile_catalog import MANUAL_MOBILES, SHOT_LABELS, display_name, catalog_records, filter_records, is_recommended
from theme import BG,PANEL,FIELD,TEXT,MUTED,GREEN,LINE,FONT,MONO
from rounded_widgets import RoundedButton
from rounded_controls import RoundedChoice,RoundedEntry,RoundedSwitch


def style_tables(win):
    from desktop_shell import style_window
    style_window(win)
    style=ttk.Style(win)
    style.configure('Catalog.Treeview',background=PANEL,fieldbackground=PANEL,foreground=TEXT,
                    rowheight=30,borderwidth=0,font=(FONT,10))
    style.configure('Catalog.Treeview.Heading',background=FIELD,foreground=MUTED,
                    font=(FONT,10,'bold'),padding=(8,9),relief='flat')
    style.map('Catalog.Treeview',background=[('selected',FIELD)],foreground=[('selected',GREEN)])
    style.map('Catalog.Treeview.Heading',background=[('active',FIELD)])
    style.configure('Catalog.TCombobox',fieldbackground=FIELD,background=FIELD,foreground=TEXT,
                    arrowcolor=GREEN,padding=5)
    style.map('Catalog.TCombobox',fieldbackground=[('readonly',FIELD)],foreground=[('readonly',TEXT)])
    style.configure('TScrollbar',background=FIELD,troughcolor=PANEL,arrowcolor=MUTED,borderwidth=0)
    style.configure('TNotebook',background=BG,borderwidth=0)
    style.configure('TNotebook.Tab',background=FIELD,foreground=TEXT,padding=(12,8))
    style.map('TNotebook.Tab',background=[('selected',PANEL)],foreground=[('selected',GREEN)])


def _range(value):
    return 'Pendiente' if not value else ' – '.join(f'{v:g}' if isinstance(v,(int,float)) else str(v) for v in value)


def details_text(row):
    lines=[f"{row['game_name']} / {row['name']} / bala {row['shot_label']}",
           f"ID nativo {row['native_id']} · catálogo v{row['schema_version']}",row['status'],'',
           f"Muestras locales/aprendidas: {row['sample_count']} · comprobaciones independientes: {row['validation_count']}",
           f"Muestras del perfil incluido: {row['builtin_sample_count']}",
           f"Fuerza medida: {_range(row['power_range'])} · escala nativa: {_range(row['native_power_range'])}",
           f"Viento medido: {_range(row['wind_range'])}"]
    if row.get('wind_domain'):lines.append(f"Dominio vectorial de viento: {_range(row['wind_domain'])}")
    lines+=['','Parámetros del modelo mostrado']
    for key,value in row['parameters'].items():
        if key in ('power_scale','speed_offset','gravity','wind_scale','wind_mode','muzzle_angle','muzzle_radius','native_euler_step','holdout_speed_error','holdout_acceleration_error'):
            lines.append(f"  {key}: {value:.6g}" if isinstance(value,(int,float)) else f'  {key}: {value}')
    if not row['parameters']:lines.append('  Sin parámetros propios para esta modalidad.')
    lines+=['','Fuentes y alcance']
    for source in row['evidence']:lines.append(f"  {source['source']} · {source['scope']}")
    if not row['evidence']:lines.append('  Sin evidencia registrada.')
    lines+=['','La comprobación de salida no acredita el recorrido completo ni precisión de impacto.']
    if row['special_pending']:lines.append('El mecanismo especial sigue pendiente aunque exista un ajuste de salida.')
    if row['baseline']:lines.append('El perfil base de vehículo no es una calibración de las balas 1, 2 y SS.')
    return '\n'.join(lines)


def open_catalog(app,game_id=None):
    existing=getattr(app,'catalog_window',None)
    if existing and existing.winfo_exists():
        if game_id:
            profile=get_profile(game_id)
            if profile:existing.catalog_game.set(profile['name'])
        existing.lift();return existing
    win=tk.Toplevel(getattr(app,'ui_parent',None) or app.root);app.catalog_window=win
    win.title('DragonLab · Catálogo');win.geometry('1020x700');win.minsize(650,490);win.configure(bg=BG)
    style_tables(win)
    header=tk.Frame(win,bg=BG);header.pack(fill='x',padx=22,pady=(18,12))
    tk.Label(header,text='Carros y balas',bg=BG,fg=TEXT,font=(FONT,23,'bold')).pack(anchor='w')
    tk.Label(header,text='Consulta modelos, límites y evidencia de cada modalidad.',bg=BG,fg=MUTED,font=(FONT,10)).pack(anchor='w',pady=(4,0))
    filters=tk.Frame(win,bg=BG);filters.pack(fill='x',padx=22,pady=(0,12))
    filters.grid_columnconfigure(0,weight=1)
    win.catalog_search=tk.StringVar(win)
    entry=RoundedEntry(filters,textvariable=win.catalog_search,bg=FIELD,fg=TEXT,insertbackground=GREEN,
                   font=(FONT,-13));entry.grid(row=1,column=0,sticky='ew',padx=(0,10))
    tk.Label(filters,text='BUSCAR',bg=BG,fg=MUTED,font=(FONT,9)).grid(row=0,column=0,sticky='w',pady=(0,5))
    profiles=registered_profiles();names={p['name']:p['id'] for p in profiles}
    selected=get_profile(game_id or getattr(app,'clone_id','dragonbound'))
    win.catalog_game=tk.StringVar(win,value=selected['name'] if selected else 'Todos')
    win.catalog_mobile=tk.StringVar(win,value='Todos')
    win.catalog_shot=tk.StringVar(win,value='Todas')
    for column,(label,var,values,width) in enumerate((
        ('JUEGO',win.catalog_game,['Todos',*names],19),
        ('CARRO',win.catalog_mobile,['Todos',*MANUAL_MOBILES],15),
        ('BALA',win.catalog_shot,['Todas',*SHOT_LABELS],7)),1):
        tk.Label(filters,text=label,bg=BG,fg=MUTED,font=(FONT,9)).grid(row=0,column=column,sticky='w',pady=(0,5))
        RoundedChoice(filters,textvariable=var,values=values,width=width,state='readonly',
                     font=(FONT,-12)).grid(row=1,column=column,sticky='ew',padx=(0,8) if column<3 else 0)
    win.catalog_validated=tk.BooleanVar(win,value=False)
    RoundedSwitch(filters,text='Solo modelos validados',variable=win.catalog_validated,bg=BG,fg=TEXT,
        font=(FONT,-13)).grid(row=2,column=0,columnspan=4,sticky='w',pady=(9,0))
    panes=tk.PanedWindow(win,orient='horizontal',bg=BG,bd=0,sashwidth=8,sashrelief='flat')
    panes.pack(fill='both',expand=True,padx=22)
    left=tk.Frame(panes,bg=PANEL);right=tk.Frame(panes,bg=PANEL);panes.add(left,minsize=300,stretch='always');panes.add(right,minsize=230,stretch='always')
    columns=('game','mobile','shot','state','count')
    table=ttk.Treeview(left,columns=columns,show='headings',selectmode='browse',style='Catalog.Treeview')
    win.catalog_table=table
    for key,label,width in (('game','Juego',140),('mobile','Carro',130),('shot','Bala',45),('state','Estado',230),('count','Tiros',50)):
        table.heading(key,text=label);table.column(key,width=width,minwidth=40,stretch=key in ('mobile','state'))
    sy=ttk.Scrollbar(left,orient='vertical',command=table.yview);sx=ttk.Scrollbar(left,orient='horizontal',command=table.xview)
    table.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
    table.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
    left.grid_rowconfigure(0,weight=1);left.grid_columnconfigure(0,weight=1)
    detail=tk.Text(right,bg=PANEL,fg=TEXT,relief='flat',wrap='word',font=(FONT,11),
                   padx=16,pady=15,insertwidth=0,state='disabled',width=38)
    detail.pack(side='left',fill='both',expand=True);dy=ttk.Scrollbar(right,command=detail.yview);dy.pack(side='right',fill='y');detail.configure(yscrollcommand=dy.set)
    win.catalog_detail=detail
    footer=tk.Frame(win,bg=BG);footer.pack(fill='x',padx=22,pady=14)
    count=tk.Label(footer,bg=BG,fg=MUTED,font=(FONT,10),anchor='w');count.pack(side='left',fill='x',expand=True);win.catalog_count=count
    def show_detail(_event=None):
        selected=table.selection();row=win.catalog_rows.get(selected[0]) if selected else None
        profile=get_profile(names.get(win.catalog_game.get()))
        text=details_text(row) if row else ('\n'.join([profile['name'],profile['limits'],
            'Dominio observado: '+', '.join(profile.get('observed_hosts',[])),*profile['evidence']])
            if profile and profile['status']!='supported' else 'Selecciona una modalidad para consultar sus parámetros y fuentes.')
        if detail.get('1.0','end-1c')!=text:
            position=detail.yview();detail.configure(state='normal');detail.delete('1.0','end');detail.insert('1.0',text);detail.configure(state='disabled')
            if position:detail.yview_moveto(position[0])
    def review():
        selected=table.selection();row=win.catalog_rows.get(selected[0]) if selected else None
        if not row:return None
        from calibration_ui import open_calibration
        return open_calibration(app,row['game_id'],row['mobile'],row['shot'])
    review_button=RoundedButton(footer,text='Revisar calibración',command=review,font=(FONT,10),bg=FIELD,fg=TEXT)
    review_button.pack(side='right');win.catalog_review_button=review_button
    def refresh(*_):
        selection=table.selection();selected=selection[0] if selection else None
        selected_game=names.get(win.catalog_game.get());label=win.catalog_shot.get()
        rows=filter_records(catalog_records(app),win.catalog_search.get(),selected_game,
                            None if win.catalog_mobile.get()=='Todos' else win.catalog_mobile.get(),
                            SHOT_LABELS.index(label) if label in SHOT_LABELS else None)
        matching=len(rows);validated=sum(is_recommended(row) for row in rows)
        if win.catalog_validated.get():rows=[row for row in rows if is_recommended(row)]
        win.catalog_rows={r['key']:r for r in rows}
        old=set(table.get_children());current=set(win.catalog_rows)
        for key in old-current:table.delete(key)
        for index,row in enumerate(rows):
            values=(row['game_name'],row['name'],row['shot_label'],row['status'],row['sample_count'])
            if table.exists(row['key']):table.item(row['key'],values=values)
            else:table.insert('','end',iid=row['key'],values=values)
            table.move(row['key'],'',index)
        profile=get_profile(selected_game)
        count.configure(text=f'{len(rows)} de {matching} modalidades · {validated} validadas' if matching else
            'Solo metadatos · sin modalidades' if profile and profile['status']!='supported' else 'Sin coincidencias')
        review_button.configure(state='normal' if rows else 'disabled')
        if rows:
            key=selected if selected in win.catalog_rows else rows[0]['key']
            if not table.selection() or table.selection()[0]!=key:table.selection_set(key);table.focus(key)
        show_detail()
    win.refresh_catalog=refresh
    for var in (win.catalog_search,win.catalog_game,win.catalog_mobile,win.catalog_shot,win.catalog_validated):var.trace_add('write',refresh)
    table.bind('<<TreeviewSelect>>',show_detail);table.bind('<Double-1>',lambda e:review())
    win.bind('<Escape>',lambda e:win.destroy())
    def tick():
        if win.winfo_exists():refresh();win.refresh_job=win.after(2000,tick)
    def cancel(event):
        if event.widget==win and getattr(win,'refresh_job',None):
            try:win.after_cancel(win.refresh_job)
            except tk.TclError:pass
    win.bind('<Destroy>',cancel);tick();return win
