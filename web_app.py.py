import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
import re
from datetime import datetime
import threading

# 구글 API 라이브러리 체크
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_INSTALLED = True
except ImportError:
    GSPREAD_INSTALLED = False

class GuildManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("조선협객전 클래식 - [오늘만산다]")
        self.root.geometry("1450x980")
        
        # 🎨 테마 설정
        self.bg_color = "#050505"; self.fg_color = "#FFFFFF"; self.neon_green = "#76B900"
        self.color_gold = "#FFD700"; self.root.configure(bg=self.bg_color)
        
        self.class_colors = {"검객": "#FF4500", "궁수": "#32CD32", "도사": "#00CED1", "승려": "#FFD700", "투사": "#BA55D3", "포수": "#F8F8FF"}
        self.sheet_name = "조협오산오살"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(current_dir, "guild_integrated_master.csv")
        self.credentials_file = os.path.join(current_dir, "credentials.json")
        
        self.game_classes = ["검객", "궁수", "도사", "승려", "투사", "포수"]
        self.guilds = ["오늘만산다", "오늘만살자"]
        
        self.participants = {}; self.class_trees = {}; self.sort_history = {} 
        self.authenticated = False 

        self.setup_styles(); self.create_widgets(); self.load_data() 
        self.root.after(100, self.refresh_all_views) 
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def setup_styles(self):
        style = ttk.Style(); style.theme_use('clam')
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabelframe", background=self.bg_color, foreground=self.neon_green, bordercolor="#444444")
        style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.neon_green, font=("Arial", 11, "bold"))
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure("TButton", background=self.neon_green, foreground="black", font=("Arial", 10, "bold"))
        style.configure("Sync.TButton", background="#007BFF", foreground="white", font=("Arial", 10, "bold"))
        style.configure("Reset.TButton", background="#FF4444", foreground="white", font=("Arial", 10, "bold"))
        style.configure("Treeview", background="#151515", foreground="#FFFFFF", fieldbackground="#151515", borderwidth=0, rowheight=35)
        style.configure("Treeview.Heading", background="#000000", foreground=self.neon_green, font=("Arial", 10, "bold"))
        style.map("Treeview", background=[('selected', self.neon_green)], foreground=[('selected', 'black')])
        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab", background="#222222", foreground="#888888", padding=[20, 10])
        style.map("TNotebook.Tab", background=[("selected", self.neon_green)], foreground=[("selected", "black")])

    def create_widgets(self):
        self.side_frame = tk.Frame(self.root, bg="#111", width=180); self.side_frame.pack(side="left", fill="y")
        tk.Label(self.side_frame, text="🔐 ADMIN", bg="#111", fg=self.neon_green, font=("Arial", 10, "bold")).pack(pady=10)
        self.pw_entry = tk.Entry(self.side_frame, show="*", width=15, bg="#222", fg="white", justify="center"); self.pw_entry.pack(pady=5)
        tk.Button(self.side_frame, text="인증", command=self.check_auth, bg=self.neon_green, fg="black", width=10).pack(pady=5)

        self.notebook = ttk.Notebook(self.root); self.notebook.pack(fill="both", expand=True, padx=20, pady=20)
        self.tab_boss = ttk.Frame(self.notebook); self.tab_cp = ttk.Frame(self.notebook); self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_rank = ttk.Frame(self.notebook); self.tab_money = ttk.Frame(self.notebook)
        for t, txt in [(self.tab_boss, "⚔️ 출석/보스"), (self.tab_cp, "🛡️ 전력/성장"), (self.tab_dashboard, "📊 대시보드"), (self.tab_rank, "🏆 랭킹"), (self.tab_money, "💰 정산")]:
            self.notebook.add(t, text=txt)
        
        self.build_boss_tab(); self.build_cp_tab(); self.build_dashboard_tab(); self.build_rank_tab(); self.build_money_tab()

    def check_auth(self):
        if self.pw_entry.get() == "rkdhkdthfdl12":
            self.authenticated = True; messagebox.showinfo("성공", "관리자 모드 활성화"); self.pw_entry.delete(0, tk.END)
        else: messagebox.showerror("오류", "비밀번호 불일치")

    def build_boss_tab(self):
        stats_f = ttk.LabelFrame(self.tab_boss, text=" [ 📊 오늘 보스 참여 현황 ] "); stats_f.pack(pady=10, padx=15, fill="x")
        self.boss_summary_lbl = ttk.Label(stats_f, text="분석 중...", font=("Arial", 11, "bold"), foreground=self.color_gold); self.boss_summary_lbl.pack(pady=10)
        smart_f = ttk.LabelFrame(self.tab_boss, text=" [ 📝 데이터 제어 센터 ] "); smart_f.pack(pady=5, padx=15, fill="x")
        self.batch_text = tk.Text(smart_f, height=3, bg="#1a1a1a", fg="#ffffff", font=("Arial", 10)); self.batch_text.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        btn_grid = ttk.Frame(smart_f); btn_grid.pack(side="right", padx=10)
        ttk.Button(btn_grid, text="☁️ 구글 동기화", width=12, style="Sync.TButton", command=self.trigger_google_sync).pack(pady=2)
        for s in ["14:00", "18:00", "22:00"]: ttk.Button(btn_grid, text=f"{s} 체크", width=12, command=lambda _s=s: self.smart_batch_check(_s)).pack(pady=1)
        ttk.Button(btn_grid, text="✅ 오늘 마감", width=12, command=self.reset_daily_checks).pack(pady=2)
        ttk.Button(btn_grid, text="🔥 시즌 초기화", width=12, style="Reset.TButton", command=self.reset_season_data).pack(pady=5)
        
        cols = ("문파", "이름", "14시", "18시", "22시", "총 누적")
        self.boss_tree = ttk.Treeview(self.tab_boss, columns=cols, show="headings", height=18)
        for c in cols: self.boss_tree.heading(c, text=c, command=lambda _c=c: self.sort_treeview(self.boss_tree, _c, False)); self.boss_tree.column(c, width=100, anchor="center")
        self.boss_tree.pack(fill="both", expand=True, padx=15, pady=5); self.boss_tree.bind("<Double-1>", self.on_boss_double_click)

    def build_cp_tab(self):
        stats_f = ttk.LabelFrame(self.tab_cp, text=" [ 📈 통합 통계 지표 ] "); stats_f.pack(pady=10, padx=15, fill="x")
        self.guild_stats_lbl = ttk.Label(stats_f, text="분석 중...", font=("Arial", 10, "bold"), foreground=self.color_gold); self.guild_stats_lbl.pack(pady=10)
        edit_f = ttk.LabelFrame(self.tab_cp, text=" [ 인원 관리 ] "); edit_f.pack(pady=5, padx=15, fill="x")
        input_f = ttk.Frame(edit_f); input_f.pack(pady=10, padx=10)
        self.cp_guild_var = tk.StringVar(value=self.guilds[0]); ttk.Combobox(input_f, textvariable=self.cp_guild_var, values=self.guilds, width=10, state="readonly").grid(row=0, column=0, padx=5)
        self.cp_name_entry = tk.Entry(input_f, width=15, bg="#333333", fg="#FFFFFF"); self.cp_name_entry.grid(row=0, column=1, padx=5)
        self.class_var = tk.StringVar(value="검객"); ttk.Combobox(input_f, textvariable=self.class_var, values=self.game_classes, width=8, state="readonly").grid(row=0, column=2, padx=5)
        self.cp_entry = tk.Entry(input_f, width=12, bg="#333333", fg="#FFFFFF"); self.cp_entry.grid(row=0, column=3, padx=5)
        self.kakao_var = tk.StringVar(value="O"); ttk.Combobox(input_f, textvariable=self.kakao_var, values=["O", "X"], width=3, state="readonly").grid(row=0, column=4, padx=5)
        btn_f = ttk.Frame(edit_f); btn_f.pack(pady=5)
        ttk.Button(btn_f, text="💾 저장/수정", command=self.update_cp_data).pack(side="left", padx=5)
        ttk.Button(btn_f, text="🗑️ 탈퇴자 삭제", command=self.delete_member).pack(side="left", padx=5)
        list_p = ttk.PanedWindow(self.tab_cp, orient=tk.HORIZONTAL); list_p.pack(fill="both", expand=True, padx=15, pady=10)
        self.tree_guild1 = self.create_guild_tree(list_p, "오늘만산다"); self.tree_guild2 = self.create_guild_tree(list_p, "오늘만살자")
        list_p.add(self.tree_guild1.master, weight=1); list_p.add(self.tree_guild2.master, weight=1)

    def build_dashboard_tab(self):
        self.dash_inner = ttk.Frame(self.tab_dashboard); self.dash_inner.pack(fill="both", expand=True, padx=40, pady=20)
        self.guild_total_f = ttk.LabelFrame(self.dash_inner, text=" [ 🏰 통합 전투력 ] "); self.guild_total_f.pack(fill="x", pady=10)
        self.total_cp_lbl = ttk.Label(self.guild_total_f, text="전투력: 0", font=("Arial", 18, "bold"), foreground=self.color_gold); self.total_cp_lbl.pack(pady=15)
        c_container = ttk.Frame(self.dash_inner); c_container.pack(fill="both", expand=True)
        self.chart_f = ttk.LabelFrame(c_container, text=" [ ⚔️ 직업별 성장률 ] "); self.chart_f.pack(side="left", fill="both", expand=True, padx=5)
        self.canvas_bar = tk.Canvas(self.chart_f, bg="#111111", highlightthickness=0); self.canvas_bar.pack(fill="both", expand=True)
        self.pie_f = ttk.LabelFrame(c_container, text=" [ ⚖️ 문파 비중 ] "); self.pie_f.pack(side="left", fill="both", expand=True, padx=5)
        self.canvas_pie = tk.Canvas(self.pie_f, bg="#111111", highlightthickness=0); self.canvas_pie.pack(fill="both", expand=True)
        self.mvp_f = ttk.LabelFrame(self.dash_inner, text=" [ 🔥 성장 랭킹 ] "); self.mvp_f.pack(fill="x", pady=10)
        self.mvp_tree = ttk.Treeview(self.mvp_f, columns=("순위", "이름", "문파", "성장률"), show="headings", height=5)
        for c in ("순위", "이름", "문파", "성장률"): self.mvp_tree.heading(c, text=c); self.mvp_tree.column(c, anchor="center")
        self.mvp_tree.pack(fill="x", padx=10, pady=10)

    def build_rank_tab(self):
        p = ttk.PanedWindow(self.tab_rank, orient=tk.HORIZONTAL); p.pack(fill="both", expand=True, padx=15, pady=15)
        left = ttk.LabelFrame(p, text=" 👑 통합 순위 "); p.add(left, weight=1)
        self.rank_tree_all = ttk.Treeview(left, columns=("순위", "이름", "직업", "투력"), show="headings")
        for c in ("순위", "이름", "직업", "투력"): self.rank_tree_all.heading(c, text=c); self.rank_tree_all.column(c, width=80, anchor="center")
        self.rank_tree_all.pack(fill="both", expand=True)
        right = ttk.Frame(p); p.add(right, weight=2)
        for i, cls in enumerate(self.game_classes):
            r, c = divmod(i, 2); f = ttk.LabelFrame(right, text=f" [{cls}] "); f.grid(row=r, column=c, sticky="nsew", padx=3, pady=3); right.rowconfigure(r, weight=1); right.columnconfigure(c, weight=1)
            tree = ttk.Treeview(f, columns=("순위", "문파", "이름", "투력"), show="headings", height=10)
            for tc in ("순위", "문파", "이름", "투력"): tree.heading(tc, text=tc); tree.column(tc, width=80, anchor="center")
            tree.pack(fill="both", expand=True); self.class_trees[cls] = tree

    def build_money_tab(self):
        f = ttk.LabelFrame(self.tab_money, text=" [ 💰 정산기 ] "); f.pack(pady=20, padx=20, fill="x")
        self.total_money_entry = tk.Entry(f, width=15, bg="#333333", fg="white", font=("Arial", 12)); self.total_money_entry.grid(row=0, column=1)
        ttk.Button(f, text="정산 실행", command=self.calculate_distribution).grid(row=0, column=2, padx=20)
        self.money_tree = ttk.Treeview(self.tab_money, columns=("이름", "투력", "참여", "분배금"), show="headings", height=20)
        for c in ("이름", "투력", "참여", "분배금"): self.money_tree.heading(c, text=c); self.money_tree.column(c, width=120, anchor="center"); self.money_tree.pack(fill="both", expand=True, padx=20, pady=10)

    def reset_daily_checks(self):
        if not messagebox.askyesno("일일 마감", "오늘 참여 기록을 누적으로 합산하고 비웁니까?"): return
        for n in self.participants:
            d = self.participants[n]; today = [d.get("14:00","X"), d.get("18:00","X"), d.get("22:00","X")].count("O")
            d["base_total"] = d.get("base_total", 0) + today
            d["14:00"]=d["18:00"]=d["22:00"]="X"
        self.refresh_all_views(); self.save_data(); self.trigger_google_sync()
        messagebox.showinfo("성공", "일일 마감 및 구글 동기화 완료")

    def reset_season_data(self):
        if not self.authenticated: messagebox.showwarning("권한","ADMIN 인증 필요"); return
        if not messagebox.askyesno("시즌 초기화", "모든 데이터를 0으로 초기화합니까?"): return
        for n in self.participants: self.participants[n].update({"base_total":0, "14:00":"X", "18:00":"X", "22:00":"X"})
        self.refresh_all_views(); self.save_data()
        threading.Thread(target=self._sync_reset_thread, daemon=True).start()

    def _sync_reset_thread(self):
        try:
            gc = gspread.service_account(filename=self.credentials_file)
            sh = gc.open(self.sheet_name); ws = sh.sheet1; h = ws.get_all_values()[6]
            n_idx, s_idx, m_idx = h.index("누계")+1, h.index("정산상태")+1, h.index("분배금")+1
            r_cnt = len(self.participants)
            for idx, val in [(n_idx, '0'), (m_idx, '0'), (s_idx, '미정산')]:
                cells = ws.range(8, idx, 7+r_cnt, idx)
                for c in cells: c.value = val
                ws.update_cells(cells)
            self.trigger_google_sync()
        except Exception as e: messagebox.showerror("초기화 오류", str(e))

    def trigger_google_sync(self):
        if not GSPREAD_INSTALLED: messagebox.showerror("오류", "gspread 미설치"); return
        threading.Thread(target=self._sync_thread, daemon=True).start()

    def _sync_thread(self):
        try:
            gc = gspread.service_account(filename=self.credentials_file)
            sh = gc.open(self.sheet_name); ws = sh.sheet1; existing = ws.get_all_values()
            status_backup = {}
            if len(existing) > 7:
                h = existing[6]; s_i, n_i = h.index("정산상태"), h.index("이름")
                for r in existing[7:]: status_backup[r[n_i]] = r[s_i] if len(r) > s_i else "미정산"
            
            names = [self.boss_tree.item(i)['values'][1] for i in self.boss_tree.get_children()]
            matrix = [["" for _ in range(12)] for _ in range(70)]
            matrix[0][0] = f"📊 통합 현황 ({datetime.now().strftime('%m/%d %H:%M')})"
            matrix[6][0:12] = ["문파", "이름", "직업", "전투력", "14시", "18시", "22시", "누계", "성장", "카톡", "분배금", "정산상태"]
            
            t_dia = 0
            try: t_dia = int(self.total_money_entry.get().replace(',', ''))
            except: pass
            
            def get_sc(d):
                if d['cp'] <= 1: return 0
                c = (1.0 if d['cp']>=200000 else 0.9 if d['cp']>=190000 else 0.8 if d['cp']>=180000 else 0.7 if d['cp']>=170000 else 0.6 if d['cp']>=150000 else 0.5 if d['cp']>=130000 else 0.4 if d['cp']>=110000 else 0.3 if d['cp']>=90000 else 0.2 if d['cp']>=70000 else 0.1)
                return self.get_total(d) * c
            
            ts = sum([get_sc(d) for d in self.participants.values()])
            for i, n in enumerate(names[:60]):
                if n not in self.participants: continue
                d = self.participants[n]; sc = get_sc(d); dist = int((sc/ts)*t_dia) if ts > 0 else 0
                matrix[i+7][0:12] = [d["guild"], n, d["class"], d["cp"], d.get("14:00","X"), d.get("18:00","X"), d.get("22:00","X"), f"{self.get_total(d)}회", d.get("growth","-"), d.get("kakao","X"), f"{dist:,}", status_backup.get(n, "미정산")]
            
            ws.clear(); ws.update(values=matrix, range_name='A1')
            self.root.after(0, lambda: messagebox.showinfo("성공", "동기화 완료"))
        except Exception as e: self.root.after(0, lambda: messagebox.showerror("실패", str(e)))

    def create_guild_tree(self, parent, title):
        frame = ttk.LabelFrame(parent, text=f" [{title}] ")
        cols = ("이름", "직업", "전투력", "누계", "성장(율)", "카톡")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=18)
        for c in cols: tree.heading(c, text=c, command=lambda _t=tree, _c=c: self.sort_treeview(_t, _c, False)); tree.column(c, width=95, anchor="center")
        tree.pack(fill="both", expand=True, padx=5, pady=5); tree.bind("<<TreeviewSelect>>", lambda e: self.on_tree_select(tree)); return tree

    def refresh_all_views(self):
        if not self.participants: return
        g_c, g_cp = {g:0 for g in self.guilds}, {g:0 for g in self.guilds}
        t14, t18, t22 = 0, 0, 0
        for d in self.participants.values():
            if d['guild'] in g_c: g_c[d['guild']]+=1; g_cp[d['guild']]+=d['cp']
            if d.get("14:00")=="O": t14+=1
            if d.get("18:00")=="O": t18+=1
            if d.get("22:00")=="O": t22+=1
        self.boss_summary_lbl.config(text=f"📢 참여현황 [ 14시: {t14} ] | [ 18시: {t18} ] | [ 22시: {t22} ] / {len(self.participants)}명")
        self.guild_stats_lbl.config(text=" | ".join([f"{g}: {g_c[g]}명" for g in self.guilds]))
        self.total_cp_lbl.config(text=f"전체 연합 전투력: {sum(g_cp.values()):,}")

        for t in [self.tree_guild1, self.tree_guild2, self.boss_tree, self.rank_tree_all, self.mvp_tree]:
            for i in t.get_children(): t.delete(i)
        for g_n, t_t in [("오늘만산다", self.tree_guild1), ("오늘만살자", self.tree_guild2)]:
            g_m = sorted([(n, d) for n, d in self.participants.items() if d["guild"]==g_n], key=lambda x:x[1]["cp"], reverse=True)
            for r, (n, d) in enumerate(g_m, 1): t_t.insert("", "end", values=(n, d["class"], f"{d['cp']:,}", f"{self.get_total(d)}회", d.get("growth","-"), d.get("kakao","X")))
        for n, d in self.participants.items(): self.boss_tree.insert("", "end", values=(d["guild"], n, d["14:00"], d["18:00"], d["22:00"], f"{self.get_total(d)}회"))
        cp_s = sorted(self.participants.items(), key=lambda x:x[1]["cp"], reverse=True)
        for r, (n, d) in enumerate(cp_s, 1): self.rank_tree_all.insert("", "end", values=(f"{r}위", n, d["class"], f"{d['cp']:,}"))
        for cls, tree in self.class_trees.items():
            for i in tree.get_children(): tree.delete(i)
            cls_m = sorted([(n, d) for n, d in self.participants.items() if d["class"]==cls], key=lambda x:x[1]["cp"], reverse=True)
            for r, (n, d) in enumerate(cls_m, 1): tree.insert("", "end", values=(f"{r}위", d["guild"], n, f"{d['cp']:,}"))
        self.save_data()

    def calculate_distribution(self):
        try:
            total = int(self.total_money_entry.get().replace(',', '')); p_s, t_s = [], 0
            for n, d in self.participants.items():
                cnt = self.get_total(d)
                if cnt > 0 and d['cp'] > 1:
                    cp = d['cp']; coef = (1.0 if cp>=200000 else 0.9 if cp>=190000 else 0.8 if cp>=180000 else 0.7 if cp>=170000 else 0.6 if cp>=150000 else 0.5 if cp>=130000 else 0.4 if cp>=110000 else 0.3 if cp>=90000 else 0.2 if cp>=70000 else 0.1)
                    sc = cnt * coef; t_s += sc; p_s.append({"n": n, "cp": cp, "ct": cnt, "sc": sc})
            for i in self.money_tree.get_children(): self.money_tree.delete(i)
            p_s.sort(key=lambda x: x["sc"], reverse=True)
            for p in p_s:
                sh = int((p["sc"]/t_s)*total) if t_s > 0 else 0
                self.money_tree.insert("", "end", values=(p["n"], f"{p['cp']:,}", f"{p['ct']}회", f"{sh:,} 다이아"))
            self.trigger_google_sync(); messagebox.showinfo("완료", "정산 완료")
        except Exception as e: messagebox.showerror("오류", str(e))

    def on_boss_double_click(self, event):
        item = self.boss_tree.identify_item(event.y); col = self.boss_tree.identify_column(event.x)
        if item and col:
            idx = int(col.replace("#", "")) - 1
            if idx in [2, 3, 4]:
                slot = ["14:00", "18:00", "22:00"][idx-2]; name = self.boss_tree.item(item, 'values')[1]
                self.participants[name][slot] = "O" if self.participants[name].get(slot, "X") == "X" else "X"; self.refresh_all_views()

    def update_cp_data(self):
        n, cp_v, g = self.cp_name_entry.get().strip(), self.cp_entry.get().strip().replace(',', ''), self.cp_guild_var.get()
        if n and cp_v.isdigit():
            new_cp = int(cp_v)
            if n in self.participants:
                old_cp = self.participants[n]["cp"]; diff = new_cp - old_cp; rate = (diff/old_cp*100) if old_cp > 0 else 0
                growth_str = f"▲{abs(diff):,} ({abs(rate):.1f}%)" if diff != 0 else "-"
                self.participants[n].update({"guild": g, "class": self.class_var.get(), "cp": new_cp, "growth": growth_str, "kakao": self.kakao_var.get()})
            else: self.participants[n] = {"guild": g, "class": self.class_var.get(), "cp": new_cp, "growth": "-", "kakao": self.kakao_var.get(), "14:00": "X", "18:00": "X", "22:00": "X", "base_total": 0}
            self.refresh_all_views()

    def delete_member(self):
        n = self.cp_name_entry.get().strip()
        if n in self.participants and messagebox.askyesno("삭제", f"[{n}] 삭제?"): del self.participants[n]; self.refresh_all_views(); self.trigger_google_sync()

    def on_tree_select(self, tree):
        sel = tree.selection()
        if sel:
            v = tree.item(sel[0])['values']; name = v[1] if tree in [self.boss_tree, self.rank_tree_all] else v[0]
            if name in self.participants:
                d = self.participants[name]; self.cp_name_entry.delete(0, tk.END); self.cp_name_entry.insert(0, name); self.cp_entry.delete(0, tk.END); self.cp_entry.insert(0, f"{d['cp']:,}"); self.cp_guild_var.set(d["guild"]); self.class_var.set(d["class"]); self.kakao_var.set(d.get("kakao", "O"))

    def get_total(self, d): return d.get("base_total", 0) + [d.get("14:00", "X"), d.get("18:00", "X"), d.get("22:00", "X")].count("O")
    def get_numeric_value(self, s):
        try:
            clean = str(s).replace(',', '').replace('▲', '').replace('▼', '').replace('회', '').replace('위', '').strip()
            if '(' in clean: clean = clean.split('(')[1].split('%')[0]
            return float(clean)
        except: return 0

    def smart_batch_check(self, slot):
        raw_text = self.batch_text.get("1.0", tk.END)
        for n in re.findall(r'[가-힣a-zA-Z0-9]+', raw_text):
            if n in self.participants: self.participants[n][slot] = "O"
        self.refresh_all_views(); self.batch_text.delete("1.0", tk.END)

    def draw_dashboard(self):
        if not self.participants: return
        self.root.update_idletasks(); self.canvas_bar.delete("all"); self.canvas_pie.delete("all")
        bw, bh = self.canvas_bar.winfo_width(), self.canvas_bar.winfo_height()
        if bw > 10:
            pad = 60; class_rates = {}
            for cls in self.game_classes:
                rates = [float(d["growth"].split("(")[1].split("%")[0]) for d in self.participants.values() if d["class"]==cls and "(" in str(d.get("growth"))]
                class_rates[cls] = sum(rates)/len(rates) if rates else 0
            max_r = max(class_rates.values()) if any(class_rates.values()) else 1.0; bar_w = (bw - (pad * 2)) / len(self.game_classes)
            for i, cls in enumerate(self.game_classes):
                val = class_rates[cls]; h_val = (val / max_r) * (bh - 140) if val > 0 else 0
                x0, y0 = pad + (i * bar_w) + 10, bh - 60 - h_val; x1, y1 = x0 + bar_w - 20, bh - 60
                color = self.class_colors.get(cls, self.neon_green)
                self.canvas_bar.create_rectangle(x0, y0, x1, y1, fill=color, outline=self.fg_color)
                self.canvas_bar.create_text((x0+x1)/2, bh-40, text=cls, fill="white", font=("Arial", 9, "bold"))
        pw, ph = self.canvas_pie.winfo_width(), self.canvas_pie.winfo_height()
        if pw > 10:
            cx, cy, r = pw/2, ph/2 - 20, min(pw, ph)/3.5
            g_totals = {g: sum([d["cp"] for d in self.participants.values() if d["guild"] == g]) for g in self.guilds}
            total_all = sum(g_totals.values()) or 1; start_ang, colors = 0, ["#76B900", "#007BFF"]
            for i, g in enumerate(self.guilds):
                per = (g_totals[g] / total_all) * 100; ext = (per / 100) * 360
                if ext > 0:
                    self.canvas_pie.create_arc(cx-r, cy-r, cx+r, cy+r, start=start_ang, extent=ext, fill=colors[i], outline="white")
                    lx, ly = 20, ph - 60 + (i * 25)
                    self.canvas_pie.create_rectangle(lx, ly, lx+15, ly+15, fill=colors[i], outline="white")
                    self.canvas_pie.create_text(lx+25, ly+7, text=f"{g}: {per:.1f}%", fill="white", font=("Arial", 9, "bold"), anchor="w")
                    start_ang += ext

    def on_tab_changed(self, e):
        if self.notebook.tab(self.notebook.select(), "text") == "📊 대시보드": self.draw_dashboard()
    def sort_treeview(self, tree, col, reverse):
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        l.sort(reverse=reverse); [tree.move(k, '', i) for i, (v, k) in enumerate(l)]
        tree.heading(col, command=lambda: self.sort_treeview(tree, col, not reverse))
    def save_data(self):
        with open(self.data_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["Guild", "Name", "Class", "CP", "T1", "T2", "T3", "BaseTotal", "Growth", "Kakao"])
            for n, d in self.participants.items(): w.writerow([d["guild"], n, d["class"], d["cp"], d["14:00"], d["18:00"], d["22:00"], d.get("base_total", 0), d.get("growth", "-"), d.get("kakao", "X")])
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8-sig") as f:
                    for r in csv.DictReader(f):
                        n = r["Name"]; self.participants[n] = {"guild": r["Guild"], "class": r["Class"], "cp": int(r["CP"]), "14:00": r["T1"], "18:00": r["T2"], "22:00": r["T3"], "base_total": int(r.get("BaseTotal", 0)), "growth": r.get("Growth", "-"), "kakao": r.get("Kakao", "X")}
                self.refresh_all_views()
            except: pass

if __name__ == "__main__":
    root = tk.Tk(); app = GuildManagerApp(root); root.mainloop()
