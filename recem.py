import shutil
import sqlite3
import subprocess
import sys
import os
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    Figure = FigureCanvasTkAgg = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    A4 = pdf_canvas = pdfmetrics = TTFont = None

DB = "imobiliaria.db"
IMG_DIR = os.path.join("recursos", "imagens")
os.makedirs(IMG_DIR, exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#0b1220"
SIDEBAR = "#1D1D2D"
CARD = "#172033"
CARD2 = "#1d293d"
BORDER = "#2b3a55"
PRIMARY = "#2563eb"
PRIMARY_H = "#1d4ed8"
SUCCESS = "#16a34a"
DANGER = "#dc2626"
TEXT = "#f8fafc"
MUTED = "#94a3b8"


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def now():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def today():
    return datetime.now().strftime("%d/%m/%Y")


def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def number(v):
    s = str(v).strip().replace("R$", "").replace(" ", "")
    if not s:
        return 0.0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def add_missing(conn, table, definitions):
    existing = columns(conn, table)
    for name, definition in definitions.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

def create_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS imoveis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        local TEXT NOT NULL,
        quartos INTEGER DEFAULT 0,
        banheiros INTEGER DEFAULT 0,
        vagas INTEGER DEFAULT 0,
        area REAL DEFAULT 0,
        valor REAL DEFAULT 0,
        descricao TEXT DEFAULT '',
        imagem TEXT DEFAULT '',
        favorito INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Disponível',
        criado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        interesse TEXT DEFAULT '',
        observacao TEXT DEFAULT '',
        criado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS visitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        imovel_id INTEGER NOT NULL,
        data TEXT NOT NULL,
        hora TEXT NOT NULL,
        observacao TEXT DEFAULT '',
        status TEXT DEFAULT 'Agendada',
        criado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS orcamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        imovel_id INTEGER NOT NULL,
        valor_imovel REAL DEFAULT 0,
        entrada REAL DEFAULT 0,
        desconto REAL DEFAULT 0,
        financiamento REAL DEFAULT 0,
        observacao TEXT DEFAULT '',
        criado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS avaliacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        imovel_id INTEGER NOT NULL,
        nota INTEGER NOT NULL,
        comentario TEXT DEFAULT '',
        criado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        imovel_id INTEGER NOT NULL,
        valor REAL NOT NULL,
        data TEXT NOT NULL,
        observacao TEXT DEFAULT ''
    );
    """)
    # Migração segura: adiciona somente colunas ausentes; nunca apaga registros.
    add_missing(c, "imoveis", {
        "titulo": "TEXT DEFAULT ''", "tipo": "TEXT DEFAULT 'Casa'", "local": "TEXT DEFAULT ''",
        "quartos": "INTEGER DEFAULT 0", "banheiros": "INTEGER DEFAULT 0", "vagas": "INTEGER DEFAULT 0",
        "area": "REAL DEFAULT 0", "valor": "REAL DEFAULT 0", "descricao": "TEXT DEFAULT ''",
        "imagem": "TEXT DEFAULT ''", "favorito": "INTEGER DEFAULT 0", "status": "TEXT DEFAULT 'Disponível'",
        "criado_em": "TEXT DEFAULT ''"
    })
    add_missing(c, "clientes", {"nome":"TEXT DEFAULT ''","telefone":"TEXT DEFAULT ''","email":"TEXT DEFAULT ''","interesse":"TEXT DEFAULT ''","observacao":"TEXT DEFAULT ''","criado_em":"TEXT DEFAULT ''"})
    add_missing(c, "visitas", {"cliente_id":"INTEGER DEFAULT 0","imovel_id":"INTEGER DEFAULT 0","data":"TEXT DEFAULT ''","hora":"TEXT DEFAULT ''","observacao":"TEXT DEFAULT ''","status":"TEXT DEFAULT 'Agendada'","criado_em":"TEXT DEFAULT ''"})
    add_missing(c, "orcamentos", {"cliente_id":"INTEGER DEFAULT 0","imovel_id":"INTEGER DEFAULT 0","valor_imovel":"REAL DEFAULT 0","entrada":"REAL DEFAULT 0","desconto":"REAL DEFAULT 0","financiamento":"REAL DEFAULT 0","observacao":"TEXT DEFAULT ''","criado_em":"TEXT DEFAULT ''"})
    add_missing(c, "avaliacoes", {"cliente_id":"INTEGER DEFAULT 0","imovel_id":"INTEGER DEFAULT 0","nota":"INTEGER DEFAULT 5","comentario":"TEXT DEFAULT ''","criado_em":"TEXT DEFAULT ''"})
    add_missing(c, "vendas", {"cliente_id":"INTEGER DEFAULT 0","imovel_id":"INTEGER DEFAULT 0","valor":"REAL DEFAULT 0","data":"TEXT DEFAULT ''","observacao":"TEXT DEFAULT ''"})
    c.commit(); c.close()

def copy_image(path):
    if not path or not os.path.isfile(path):
        return ""
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        return ""
    name = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ext
    dest = os.path.join(IMG_DIR, name)
    shutil.copy2(path, dest)
    return dest

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Recem Imóveis • Gestão Imobiliária")
        self.geometry("1400x850")
        self.minsize(1150, 700)
        self.configure(fg_color=BG)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._images = []
        self.make_sidebar()
        self.make_area()
        self.dashboard()

    def make_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        ctk.CTkLabel(self.sidebar, text="Recem Imóveis", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(30, 2))
        ctk.CTkLabel(self.sidebar, text="Sistema de Gestão", text_color=MUTED).pack(pady=(0, 28))
        for text, command in [
            ("🏠  Dashboard", self.dashboard), ("🏡  Imóveis", self.imoveis), ("👥  Clientes", self.clientes),
            ("📅  Visitas", self.visitas), ("💰  Orçamentos", self.orcamentos), ("⭐  Avaliações", self.avaliacoes),
            ("📊  Vendas", self.vendas)
        ]:
            ctk.CTkButton(self.sidebar, text=text, command=command, height=44, corner_radius=10,
                          fg_color="transparent", hover_color="#1f3b66", anchor="w",
                          font=ctk.CTkFont(size=14)).pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(self.sidebar, text="", fg_color="transparent").pack(expand=True)
        ctk.CTkLabel(self.sidebar, text="SQLite • dados locais", text_color="#64748b").pack(pady=(0, 4))
        ctk.CTkLabel(self.sidebar, text="Recem Imóveis • V2", text_color="#64748b").pack(pady=(0, 18))

    def make_area(self):
        self.area = ctk.CTkFrame(self, fg_color="transparent")
        self.area.grid(row=0, column=1, sticky="nsew", padx=25, pady=22)
        self.area.grid_columnconfigure(0, weight=1)
        self.area.grid_rowconfigure(0, weight=1)

    def clear(self):
        self._images.clear()
        for w in self.area.winfo_children(): w.destroy()

    def header(self, title, subtitle, action=None):
        f = ctk.CTkFrame(self.area, fg_color="transparent")
        f.pack(fill="x", pady=(0, 18))
        left = ctk.CTkFrame(f, fg_color="transparent"); left.pack(side="left")
        ctk.CTkLabel(left, text=title, font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left, text=subtitle, text_color=MUTED).pack(anchor="w")
        if action:
            ctk.CTkButton(f, text=action[0], command=action[1], height=40).pack(side="right", pady=4)

    def empty(self, parent, text):
        ctk.CTkLabel(parent, text=text, text_color=MUTED, font=ctk.CTkFont(size=16)).pack(pady=70)

    def stat(self, parent, title, value, col):
        parent.grid_columnconfigure(col, weight=1)
        f = ctk.CTkFrame(parent, corner_radius=16, fg_color=CARD, border_width=1, border_color=BORDER)
        f.grid(row=0, column=col, sticky="nsew", padx=5)
        ctk.CTkLabel(f, text=title, text_color=MUTED).pack(anchor="w", padx=18, pady=(16, 3))
        ctk.CTkLabel(f, text=value, font=ctk.CTkFont(size=23, weight="bold")).pack(anchor="w", padx=18, pady=(0, 16))

    def dashboard(self):
        self.clear(); self.header("Olá! 👋", "Resumo da sua imobiliária.")
        c = db()
        n_imoveis = c.execute("SELECT COUNT(*) FROM imoveis").fetchone()[0]
        n_clientes = c.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
        n_visitas = c.execute("SELECT COUNT(*) FROM visitas WHERE status='Agendada'").fetchone()[0]
        total = c.execute("SELECT COALESCE(SUM(valor),0) FROM vendas").fetchone()[0]
        ano = datetime.now().year
        vendas = c.execute("""SELECT substr(data,4,2) mes, SUM(valor) total FROM vendas
                             WHERE substr(data,7,4)=? GROUP BY substr(data,4,2) ORDER BY mes""", (str(ano),)).fetchall()
        tipos = c.execute("SELECT tipo, COUNT(*) qtd FROM imoveis GROUP BY tipo ORDER BY qtd DESC").fetchall()
        visitas = c.execute("""SELECT v.data,v.hora,c.nome cliente,i.titulo imovel FROM visitas v
                              LEFT JOIN clientes c ON c.id=v.cliente_id LEFT JOIN imoveis i ON i.id=v.imovel_id
                              WHERE v.status='Agendada' ORDER BY v.data,v.hora LIMIT 5""").fetchall()
        c.close()

        stats = ctk.CTkFrame(self.area, fg_color="transparent"); stats.pack(fill="x", pady=(0,16))
        self.stat(stats,"🏡 Imóveis",str(n_imoveis),0); self.stat(stats,"👥 Clientes",str(n_clientes),1)
        self.stat(stats,"📅 Visitas",str(n_visitas),2); self.stat(stats,"💰 Total vendido",money(total),3)

        body = ctk.CTkFrame(self.area, fg_color="transparent"); body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3); body.grid_columnconfigure(1, weight=2); body.grid_rowconfigure(0, weight=1)

        chart_card = ctk.CTkFrame(body, corner_radius=16, fg_color=CARD, border_width=1, border_color=BORDER)
        chart_card.grid(row=0,column=0,sticky="nsew",padx=(0,8)); chart_card.grid_rowconfigure(1,weight=1); chart_card.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(chart_card,text=f"📈 Vendas por mês • {ano}",font=ctk.CTkFont(size=19,weight="bold")).grid(row=0,column=0,sticky="w",padx=20,pady=(16,5))
        if Figure and FigureCanvasTkAgg:
            months=[f"{i:02d}" for i in range(1,13)]; vals={r["mes"]:float(r["total"] or 0) for r in vendas}
            labels=["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
            values=[vals.get(m,0) for m in months]
            fig=Figure(figsize=(7,3.4),dpi=90); fig.patch.set_facecolor("#1F3159"); ax=fig.add_subplot(111); ax.set_facecolor("#1C3261")
            ax.plot(labels,values,marker="o",linewidth=2.5); ax.fill_between(range(12),values,alpha=.12)
            ax.grid(axis="y",alpha=.18); ax.set_ylabel("R$"); ax.tick_params(axis="both",labelsize=8); ax.spines[:].set_visible(False)
            fig.tight_layout(pad=1.2)
            canvas=FigureCanvasTkAgg(fig,master=chart_card); canvas.draw(); canvas.get_tk_widget().grid(row=1,column=0,sticky="nsew",padx=12,pady=(0,12))
        else:
            self.empty(chart_card,"Instale matplotlib para visualizar o gráfico.")

        side = ctk.CTkFrame(body, corner_radius=16, fg_color=CARD, border_width=1, border_color=BORDER)
        side.grid(row=0,column=1,sticky="nsew",padx=(8,0)); side.grid_rowconfigure(3,weight=1)
        ctk.CTkLabel(side,text="📅 Próximas visitas",font=ctk.CTkFont(size=18,weight="bold")).pack(anchor="w",padx=18,pady=(18,8))
        if not visitas: self.empty(side,"Nenhuma visita agendada.")
        else:
            for v in visitas:
                ctk.CTkLabel(side,text=f"📅 {v['data']} • {v['hora']}\n👤 {v['cliente'] or 'Cliente removido'}\n🏠 {v['imovel'] or 'Imóvel removido'}",justify="left",anchor="w").pack(fill="x",padx=18,pady=8)
        ctk.CTkLabel(side,text="🏘 Imóveis por categoria",font=ctk.CTkFont(size=18,weight="bold")).pack(anchor="w",padx=18,pady=(18,8))
        if tipos:
            for t in tipos: ctk.CTkLabel(side,text=f"{t['tipo']}: {t['qtd']}",text_color=MUTED).pack(anchor="w",padx=22,pady=3)
        else: ctk.CTkLabel(side,text="Nenhum imóvel cadastrado.",text_color=MUTED).pack(anchor="w",padx=22)

    # ---------------- IMÓVEIS ----------------
    def imoveis(self):
        self.clear(); self.header("🏡 Imóveis","Gerencie casas, apartamentos, sobrados e mansões.",("＋ Novo imóvel",self.novo_imovel))
        bar=ctk.CTkFrame(self.area,fg_color="transparent"); bar.pack(fill="x",pady=(0,12))
        self.search=ctk.CTkEntry(bar,placeholder_text="🔎 Buscar por título ou localização",height=40); self.search.pack(side="left",fill="x",expand=True,padx=(0,8))
        self.type_filter=ctk.CTkComboBox(bar,values=["Todos","Casa","Apartamento","Sobrado","Mansão"],width=160,height=40); self.type_filter.set("Todos"); self.type_filter.pack(side="left",padx=4)
        self.status_filter=ctk.CTkComboBox(bar,values=["Todos","Disponível","Vendido"],width=145,height=40); self.status_filter.set("Todos"); self.status_filter.pack(side="left",padx=4)
        ctk.CTkButton(bar,text="🔎 Buscar",height=40,width=100,command=self.load_imoveis).pack(side="left",padx=4)
        self.property_list=ctk.CTkScrollableFrame(self.area,corner_radius=16,fg_color=CARD); self.property_list.pack(fill="both",expand=True)
        self.load_imoveis()

    def load_imoveis(self):
        for w in self.property_list.winfo_children(): w.destroy()
        q=self.search.get().strip(); typ=self.type_filter.get(); status=self.status_filter.get(); c=db()
        sql="SELECT * FROM imoveis WHERE (titulo LIKE ? OR local LIKE ? OR descricao LIKE ?)"; p=[f"%{q}%"]*3
        if typ!="Todos": sql+=" AND tipo=?"; p.append(typ)
        if status!="Todos": sql+=" AND status=?"; p.append(status)
        sql+=" ORDER BY id DESC"; rows=c.execute(sql,p).fetchall(); c.close()
        if not rows: self.empty(self.property_list,"🏠\n\nNenhum imóvel encontrado."); return
        for row in rows: self.property_card(row)

    def property_card(self,r):
        card=ctk.CTkFrame(self.property_list,corner_radius=14,fg_color=CARD2,border_width=1,border_color=BORDER); card.pack(fill="x",padx=8,pady=7)
        card.grid_columnconfigure(1,weight=1)
        photo=ctk.CTkFrame(card,width=190,height=135,corner_radius=12,fg_color="#0f172a"); photo.grid(row=0,column=0,padx=15,pady=15); photo.grid_propagate(False)
        path=r["imagem"] or ""
        if path and not os.path.isabs(path): path=os.path.abspath(path)
        if path and os.path.exists(path):
            try:
                im=Image.open(path).convert("RGB"); im.thumbnail((180,125)); pic=ImageTk.PhotoImage(im); self._images.append(pic)
                ctk.CTkLabel(photo,text="",image=pic).pack(expand=True)
            except Exception: ctk.CTkLabel(photo,text="🏠",font=ctk.CTkFont(size=42)).pack(expand=True)
        else: ctk.CTkLabel(photo,text="🏠",font=ctk.CTkFont(size=42)).pack(expand=True)
        info=ctk.CTkFrame(card,fg_color="transparent"); info.grid(row=0,column=1,sticky="nsew",pady=15)
        fav="❤️" if r["favorito"] else "🤍"; status="🟢" if r["status"]=="Disponível" else "🔴"
        ctk.CTkLabel(info,text=f"{r['titulo']}  {fav}",font=ctk.CTkFont(size=19,weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info,text=f"{r['tipo']} • {status} {r['status']}\n📍 {r['local']}\n🛏 {r['quartos']}  •  🚿 {r['banheiros']}  •  🚗 {r['vagas']}  •  📐 {r['area']} m²",text_color=MUTED,justify="left").pack(anchor="w",pady=5)
        ctk.CTkLabel(info,text=money(r["valor"]),font=ctk.CTkFont(size=18,weight="bold")).pack(anchor="w")
        buttons=ctk.CTkFrame(card,fg_color="transparent"); buttons.grid(row=0,column=2,padx=15)
        ctk.CTkButton(buttons,text="👁 Ver",width=105,command=lambda i=r["id"]:self.details(i)).pack(pady=3)
        ctk.CTkButton(buttons,text=fav,width=105,command=lambda i=r["id"]:self.favorite(i)).pack(pady=3)
        ctk.CTkButton(buttons,text="✏ Editar",width=105,command=lambda i=r["id"]:self.edit_imovel(i)).pack(pady=3)
        ctk.CTkButton(buttons,text="🗑 Excluir",width=105,fg_color=DANGER,hover_color="#991b1b",command=lambda i=r["id"]:self.delete_imovel(i)).pack(pady=3)

    def favorite(self,i):
        c=db(); c.execute("UPDATE imoveis SET favorito=CASE favorito WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(i,)); c.commit(); c.close(); self.load_imoveis()

    def delete_imovel(self,i):
        if not messagebox.askyesno("Excluir","Excluir este imóvel?\nO histórico de vendas e orçamentos não será apagado."): return
        c=db(); c.execute("DELETE FROM imoveis WHERE id=?",(i,)); c.commit(); c.close(); self.load_imoveis()

    def form_imovel(self, edit_id=None):
        c=db(); old=c.execute("SELECT * FROM imoveis WHERE id=?",(edit_id,)).fetchone() if edit_id else None; c.close()
        w=ctk.CTkToplevel(self); w.title("Editar imóvel" if old else "Novo imóvel"); w.geometry("620x760"); w.grab_set()
        frame=ctk.CTkScrollableFrame(w,fg_color="transparent"); frame.pack(fill="both",expand=True,padx=10,pady=5)
        ctk.CTkLabel(frame,text="✏ Editar imóvel" if old else "🏡 Cadastrar imóvel",font=ctk.CTkFont(size=25,weight="bold")).pack(pady=15)
        entries={}
        def field(label, value="", placeholder=""):
            ctk.CTkLabel(frame,text=label).pack(anchor="w",padx=25,pady=(5,2)); e=ctk.CTkEntry(frame,height=38,placeholder_text=placeholder); e.pack(fill="x",padx=25,pady=(0,7));
            if value is not None: e.insert(0,str(value))
            entries[label]=e
        field("Título",old["titulo"] if old else "","Casa moderna no Centro")
        field("Localização",old["local"] if old else "","Cidade - Estado")
        ctk.CTkLabel(frame,text="Tipo").pack(anchor="w",padx=25,pady=(5,2)); typ=ctk.CTkComboBox(frame,values=["Casa","Apartamento","Sobrado","Mansão"],height=38); typ.set(old["tipo"] if old else "Casa"); typ.pack(fill="x",padx=25,pady=(0,7))
        for lab, default in [("Quartos",0),("Banheiros",0),("Vagas",0),("Área",0),("Valor",0)]: field(lab,old[lab.lower()] if old and lab.lower() in old.keys() else default)
        ctk.CTkLabel(frame,text="Status").pack(anchor="w",padx=25,pady=(5,2)); st=ctk.CTkComboBox(frame,values=["Disponível","Vendido"],height=38); st.set(old["status"] if old else "Disponível"); st.pack(fill="x",padx=25,pady=(0,7))
        ctk.CTkLabel(frame,text="Descrição").pack(anchor="w",padx=25,pady=(5,2)); desc=ctk.CTkTextbox(frame,height=90); desc.pack(fill="x",padx=25,pady=(0,7));
        if old and old["descricao"]: desc.insert("1.0",old["descricao"])
        img={"path": old["imagem"] if old else ""}
        def choose():
            p=filedialog.askopenfilename(filetypes=[("Imagens","*.png *.jpg *.jpeg *.webp *.bmp")])
            if p: img["path"]=p; img_btn.configure(text="✅ Foto selecionada")
        img_btn=ctk.CTkButton(frame,text="🖼 Escolher foto",command=choose,height=40); img_btn.pack(fill="x",padx=25,pady=8)
        if old and old["imagem"]: img_btn.configure(text="✅ Foto atual / escolher outra")
        def save():
            try:
                title=entries["Título"].get().strip(); local=entries["Localização"].get().strip()
                if not title or not local: raise ValueError("Título e localização são obrigatórios.")
                vals=(int(entries["Quartos"].get() or 0),int(entries["Banheiros"].get() or 0),int(entries["Vagas"].get() or 0),number(entries["Área"].get()),number(entries["Valor"].get()))
                image_path=img["path"]
                if image_path and os.path.isfile(image_path) and os.path.abspath(image_path) != os.path.abspath(old["imagem"] if old and old["imagem"] else ""):
                    image_path=copy_image(image_path)
                c=db()
                if old:
                    c.execute("""UPDATE imoveis SET titulo=?,tipo=?,local=?,quartos=?,banheiros=?,vagas=?,area=?,valor=?,descricao=?,imagem=?,status=? WHERE id=?""",(title,typ.get(),local,*vals,desc.get("1.0","end").strip(),image_path,st.get(),edit_id))
                else:
                    c.execute("""INSERT INTO imoveis(titulo,tipo,local,quartos,banheiros,vagas,area,valor,descricao,imagem,favorito,status,criado_em) VALUES(?,?,?,?,?,?,?,?,?,?,0,?,?)""",(title,typ.get(),local,*vals,desc.get("1.0","end").strip(),image_path,st.get(),now()))
                c.commit(); c.close(); w.destroy(); self.imoveis(); messagebox.showinfo("Sucesso","Imóvel salvo com sucesso!")
            except Exception as e: messagebox.showerror("Erro",str(e))
        ctk.CTkButton(frame,text="💾 Salvar imóvel",height=45,command=save).pack(fill="x",padx=25,pady=15)

    def novo_imovel(self): self.form_imovel()
    def edit_imovel(self,i): self.form_imovel(i)

    def details(self,i):
        c=db(); r=c.execute("SELECT * FROM imoveis WHERE id=?",(i,)).fetchone(); reviews=c.execute("SELECT a.*,c.nome FROM avaliacoes a LEFT JOIN clientes c ON c.id=a.cliente_id WHERE a.imovel_id=? ORDER BY a.id DESC",(i,)).fetchall(); c.close()
        if not r: return
        w=ctk.CTkToplevel(self); w.title(r["titulo"]); w.geometry("780x760"); w.grab_set()
        scroll=ctk.CTkScrollableFrame(w,fg_color="transparent"); scroll.pack(fill="both",expand=True,padx=10,pady=10)
        if r["imagem"] and os.path.exists(r["imagem"]):
            try:
                im=Image.open(r["imagem"]).convert("RGB"); im.thumbnail((650,320)); pic=ImageTk.PhotoImage(im); w._pic=pic; ctk.CTkLabel(scroll,text="",image=pic).pack(pady=10)
            except Exception: pass
        ctk.CTkLabel(scroll,text=r["titulo"],font=ctk.CTkFont(size=28,weight="bold")).pack(pady=5)
        ctk.CTkLabel(scroll,text=f"{r['tipo']} • {r['status']}\n📍 {r['local']}\n🛏 {r['quartos']} quartos • 🚿 {r['banheiros']} banheiros • 🚗 {r['vagas']} vagas • 📐 {r['area']} m²",justify="center",text_color=MUTED).pack()
        ctk.CTkLabel(scroll,text=money(r["valor"]),font=ctk.CTkFont(size=23,weight="bold")).pack(pady=12)
        ctk.CTkLabel(scroll,text=r["descricao"] or "Sem descrição.",wraplength=680,justify="left").pack(anchor="w",padx=25,pady=10)
        ctk.CTkLabel(scroll,text="⭐ Avaliações",font=ctk.CTkFont(size=19,weight="bold")).pack(anchor="w",padx=25,pady=(18,8))
        if not reviews: ctk.CTkLabel(scroll,text="Nenhuma avaliação ainda.",text_color=MUTED).pack(pady=20)
        for a in reviews: ctk.CTkLabel(scroll,text=f"{'★'*int(a['nota'])}  •  {a['nome'] or 'Cliente'}\n{a['comentario'] or ''}",justify="left",anchor="w").pack(fill="x",padx=25,pady=6)

    # ---------------- CLIENTES ----------------
    def clientes(self):
        self.clear(); self.header("👥 Clientes","Cadastre clientes e registre interesses.",("＋ Novo cliente",self.novo_cliente))
        box=ctk.CTkScrollableFrame(self.area,fg_color=CARD,corner_radius=16); box.pack(fill="both",expand=True)
        c=db(); rows=c.execute("SELECT * FROM clientes ORDER BY id DESC").fetchall(); c.close()
        if not rows: self.empty(box,"👥\n\nNenhum cliente cadastrado."); return
        for r in rows:
            card=ctk.CTkFrame(box,corner_radius=14,fg_color=CARD2,border_width=1,border_color=BORDER); card.pack(fill="x",padx=8,pady=7); card.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(card,text=f"👤 {r['nome']}",font=ctk.CTkFont(size=18,weight="bold")).grid(row=0,column=0,sticky="w",padx=18,pady=(14,2))
            ctk.CTkLabel(card,text=f"📞 {r['telefone'] or '-'}   ✉️ {r['email'] or '-'}\n🏠 Interesse: {r['interesse'] or '-'}\n📝 {r['observacao'] or '-'}",text_color=MUTED,justify="left").grid(row=1,column=0,sticky="w",padx=18,pady=(0,14))
            ctk.CTkButton(card,text="🗑 Excluir",width=100,fg_color=DANGER,hover_color="#991b1b",command=lambda i=r["id"]:self.delete_client(i)).grid(row=0,column=1,rowspan=2,padx=15)

    def novo_cliente(self):
        w=ctk.CTkToplevel(self); w.title("Novo cliente"); w.geometry("520x590"); w.grab_set(); f=ctk.CTkScrollableFrame(w,fg_color="transparent"); f.pack(fill="both",expand=True)
        ctk.CTkLabel(f,text="👤 Novo cliente",font=ctk.CTkFont(size=25,weight="bold")).pack(pady=20); e={}
        for lab,ph in [("Nome","Nome completo"),("Telefone","(11) 99999-9999"),("E-mail","cliente@email.com")]:
            ctk.CTkLabel(f,text=lab).pack(anchor="w",padx=30); x=ctk.CTkEntry(f,placeholder_text=ph,height=38); x.pack(fill="x",padx=30,pady=(3,10)); e[lab]=x
        ctk.CTkLabel(f,text="Interesse").pack(anchor="w",padx=30); interest=ctk.CTkComboBox(f,values=["Casa","Apartamento","Sobrado","Mansão","Não definido"],height=38); interest.set("Não definido"); interest.pack(fill="x",padx=30,pady=(3,10))
        ctk.CTkLabel(f,text="Observação").pack(anchor="w",padx=30); obs=ctk.CTkTextbox(f,height=90); obs.pack(fill="x",padx=30)
        def save():
            if not e["Nome"].get().strip(): messagebox.showerror("Erro","Informe o nome."); return
            c=db(); c.execute("INSERT INTO clientes(nome,telefone,email,interesse,observacao,criado_em) VALUES(?,?,?,?,?,?)",(e["Nome"].get().strip(),e["Telefone"].get(),e["E-mail"].get(),interest.get(),obs.get("1.0","end").strip(),now())); c.commit(); c.close(); w.destroy(); self.clientes()
        ctk.CTkButton(f,text="💾 Salvar cliente",height=45,command=save).pack(fill="x",padx=30,pady=20)

    def delete_client(self,i):
        c=db(); uses=c.execute("SELECT COUNT(*) FROM visitas WHERE cliente_id=?",(i,)).fetchone()[0]; c.close()
        if uses: messagebox.showwarning("Cliente em uso","Este cliente possui visitas cadastradas e não pode ser excluído."); return
        if not messagebox.askyesno("Excluir","Excluir este cliente?"): return
        c=db(); c.execute("DELETE FROM clientes WHERE id=?",(i,)); c.commit(); c.close(); self.clientes()

    # ---------------- VISITAS ----------------
    def visitas(self, selected=None):
        self.clear(); self.header("📅 Visitas","Agende, conclua ou cancele visitas.",("＋ Agendar visita",lambda:self.new_visit(selected)))
        box=ctk.CTkScrollableFrame(self.area,fg_color=CARD,corner_radius=16); box.pack(fill="both",expand=True)
        c=db(); rows=c.execute("""SELECT v.*,c.nome cliente,i.titulo imovel,i.local local_imovel FROM visitas v
          LEFT JOIN clientes c ON c.id=v.cliente_id LEFT JOIN imoveis i ON i.id=v.imovel_id ORDER BY v.data,v.hora""").fetchall(); c.close()
        if not rows: self.empty(box,"📅\n\nNenhuma visita cadastrada."); return
        for r in rows:
            card=ctk.CTkFrame(box,corner_radius=14,fg_color=CARD2,border_width=1,border_color=BORDER); card.pack(fill="x",padx=8,pady=7); card.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(card,text=f"📅 {r['data']} • ⏰ {r['hora']}",font=ctk.CTkFont(size=18,weight="bold")).grid(row=0,column=0,sticky="w",padx=18,pady=(14,2))
            ctk.CTkLabel(card,text=f"👤 {r['cliente'] or 'Cliente removido'}\n🏠 {r['imovel'] or 'Imóvel removido'}\n📍 {r['local_imovel'] or '-'}\nStatus: {r['status']}\n📝 {r['observacao'] or '-'}",text_color=MUTED,justify="left").grid(row=1,column=0,sticky="w",padx=18,pady=(0,14))
            if r["status"]=="Agendada":
                b=ctk.CTkFrame(card,fg_color="transparent"); b.grid(row=0,column=1,rowspan=2,padx=15)
                ctk.CTkButton(b,text="✅ Concluir",width=110,command=lambda i=r["id"]:self.visit_status(i,"Concluída")).pack(pady=3)
                ctk.CTkButton(b,text="❌ Cancelar",width=110,fg_color=DANGER,hover_color="#991b1b",command=lambda i=r["id"]:self.visit_status(i,"Cancelada")).pack(pady=3)

    def new_visit(self,selected=None):
        c=db(); clients=c.execute("SELECT id,nome FROM clientes ORDER BY nome").fetchall(); props=c.execute("SELECT id,titulo FROM imoveis WHERE status!='Vendido' ORDER BY titulo").fetchall(); c.close()
        if not clients or not props: messagebox.showwarning("Dados necessários","Cadastre pelo menos um cliente e um imóvel disponível."); return
        w=ctk.CTkToplevel(self); w.title("Agendar visita"); w.geometry("540x650"); w.grab_set(); f=ctk.CTkScrollableFrame(w,fg_color="transparent"); f.pack(fill="both",expand=True)
        ctk.CTkLabel(f,text="📅 Agendar visita",font=ctk.CTkFont(size=25,weight="bold")).pack(pady=20)
        cd={f"{x['id']} - {x['nome']}":x['id'] for x in clients}; pd={f"{x['id']} - {x['titulo']}":x['id'] for x in props}
        def combo(label,vals): ctk.CTkLabel(f,text=label).pack(anchor="w",padx=30); b=ctk.CTkComboBox(f,values=vals,height=38); b.set(vals[0]); b.pack(fill="x",padx=30,pady=(3,10)); return b
        cb=combo("Cliente",list(cd)); pb=combo("Imóvel",list(pd))
        if selected:
            for text,i in pd.items():
                if i==selected: pb.set(text); break
        def field(label,ph): ctk.CTkLabel(f,text=label).pack(anchor="w",padx=30); x=ctk.CTkEntry(f,placeholder_text=ph,height=38); x.pack(fill="x",padx=30,pady=(3,10)); return x
        date=field("Data","DD/MM/AAAA"); time=field("Hora","HH:MM"); ctk.CTkLabel(f,text="Observação").pack(anchor="w",padx=30); obs=ctk.CTkTextbox(f,height=80); obs.pack(fill="x",padx=30)
        def save():
            try: datetime.strptime(date.get().strip(),"%d/%m/%Y"); datetime.strptime(time.get().strip(),"%H:%M")
            except ValueError: messagebox.showerror("Erro","Use Data DD/MM/AAAA e Hora HH:MM."); return
            c=db(); c.execute("INSERT INTO visitas(cliente_id,imovel_id,data,hora,observacao,status,criado_em) VALUES(?,?,?,?,?,'Agendada',?)",(cd[cb.get()],pd[pb.get()],date.get().strip(),time.get().strip(),obs.get("1.0","end").strip(),now())); c.commit(); c.close(); w.destroy(); self.visitas()
        ctk.CTkButton(f,text="📅 Agendar",height=45,command=save).pack(fill="x",padx=30,pady=20)

    def visit_status(self,i,status):
        c=db(); c.execute("UPDATE visitas SET status=? WHERE id=?",(status,i)); c.commit(); c.close(); self.visitas()

    # ---------------- ORÇAMENTOS + PDF ----------------
    def orcamentos(self):
        self.clear(); self.header("💰 Orçamentos","Crie propostas e gere PDFs.",("＋ Novo orçamento",self.new_budget))
        box=ctk.CTkScrollableFrame(self.area,fg_color=CARD,corner_radius=16); box.pack(fill="both",expand=True)
        c=db(); rows=c.execute("""SELECT o.*,c.nome cliente,i.titulo imovel FROM orcamentos o
          LEFT JOIN clientes c ON c.id=o.cliente_id LEFT JOIN imoveis i ON i.id=o.imovel_id ORDER BY o.id DESC""").fetchall(); c.close()
        if not rows: self.empty(box,"💰\n\nNenhum orçamento criado."); return
        for r in rows:
            card=ctk.CTkFrame(box,corner_radius=14,fg_color=CARD2,border_width=1,border_color=BORDER); card.pack(fill="x",padx=8,pady=7); card.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(card,text=f"👤 {r['cliente'] or 'Cliente'}\n🏠 {r['imovel'] or 'Imóvel'}\n💰 {money(r['valor_imovel'])}\nEntrada: {money(r['entrada'])}   •   Desconto: {money(r['desconto'])}\nFinanciamento: {money(r['financiamento'])}",justify="left",anchor="w").grid(row=0,column=0,sticky="w",padx=18,pady=15)
            ctk.CTkButton(card,text="📄 Gerar PDF",width=125,command=lambda i=r["id"]:self.pdf_budget(i)).grid(row=0,column=1,padx=15)

    def new_budget(self):
        c=db(); clients=c.execute("SELECT id,nome FROM clientes ORDER BY nome").fetchall(); props=c.execute("SELECT id,titulo,valor FROM imoveis ORDER BY titulo").fetchall(); c.close()
        if not clients or not props: messagebox.showwarning("Dados necessários","Cadastre pelo menos um cliente e um imóvel."); return
        w=ctk.CTkToplevel(self); w.title("Novo orçamento"); w.geometry("560x700"); w.grab_set(); f=ctk.CTkScrollableFrame(w,fg_color="transparent"); f.pack(fill="both",expand=True)
        ctk.CTkLabel(f,text="💰 Novo orçamento",font=ctk.CTkFont(size=25,weight="bold")).pack(pady=20); cd={f"{x['id']} - {x['nome']}":x['id'] for x in clients}; pd={f"{x['id']} - {x['titulo']}":x for x in props}
        def combo(label,vals): ctk.CTkLabel(f,text=label).pack(anchor="w",padx=30); b=ctk.CTkComboBox(f,values=vals,height=38); b.set(vals[0]); b.pack(fill="x",padx=30,pady=(3,10)); return b
        cb=combo("Cliente",list(cd)); pb=combo("Imóvel",list(pd))
        def field(label,val="0"): ctk.CTkLabel(f,text=label).pack(anchor="w",padx=30); x=ctk.CTkEntry(f,height=38); x.insert(0,val); x.pack(fill="x",padx=30,pady=(3,10)); return x
        value=field("Valor do imóvel",str(pd[pb.get()]["valor"])); entry=field("Entrada"); discount=field("Desconto"); finance=field("Financiamento")
        def update(*_): value.delete(0,"end"); value.insert(0,str(pd[pb.get()]["valor"]))
        pb.configure(command=update)
        ctk.CTkLabel(f,text="Observação").pack(anchor="w",padx=30); obs=ctk.CTkTextbox(f,height=80); obs.pack(fill="x",padx=30)
        def save():
            try: vals=[number(x.get()) for x in (value,entry,discount,finance)]
            except Exception: messagebox.showerror("Erro","Digite valores numéricos válidos."); return
            c=db(); c.execute("INSERT INTO orcamentos(cliente_id,imovel_id,valor_imovel,entrada,desconto,financiamento,observacao,criado_em) VALUES(?,?,?,?,?,?,?,?)",(cd[cb.get()],pd[pb.get()]["id"],*vals,obs.get("1.0","end").strip(),now())); c.commit(); c.close(); w.destroy(); self.orcamentos()
        ctk.CTkButton(f,text="💾 Salvar orçamento",height=45,command=save).pack(fill="x",padx=30,pady=20)

    def pdf_budget(self,i):
        if not pdf_canvas: messagebox.showerror("Biblioteca ausente","Instale reportlab com: pip install reportlab"); return
        c=db(); r=c.execute("""SELECT o.*,c.nome cliente,c.telefone,c.email,i.titulo imovel,i.local FROM orcamentos o
            LEFT JOIN clientes c ON c.id=o.cliente_id LEFT JOIN imoveis i ON i.id=o.imovel_id WHERE o.id=?""",(i,)).fetchone(); c.close()
        if not r: return
        path=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF","*.pdf")],initialfile=f"orcamento_{i}.pdf")
        if not path: return
        pdf=pdf_canvas.Canvas(path,pagesize=A4); W,H=A4
        # Fonte Unicode quando DejaVu existir.
        font="Helvetica"; bold="Helvetica-Bold"
        candidates=["C:/Windows/Fonts/DejaVuSans.ttf","C:/Windows/Fonts/arial.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        for fp in candidates:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("AppFont",fp)); font="AppFont"; bold="AppFont"; break
                except Exception: pass
        pdf.setFont(bold,20); pdf.drawString(50,H-60,"ORÇAMENTO IMOBILIÁRIO")
        y=H-105; pdf.setFont(font,11)
        lines=[f"Cliente: {r['cliente'] or '-'}",f"Telefone: {r['telefone'] or '-'}",f"E-mail: {r['email'] or '-'}","",f"Imóvel: {r['imovel'] or '-'}",f"Localização: {r['local'] or '-'}","",f"Valor do imóvel: {money(r['valor_imovel'])}",f"Entrada: {money(r['entrada'])}",f"Desconto: {money(r['desconto'])}",f"Financiamento: {money(r['financiamento'])}","",f"Observação: {r['observacao'] or '-'}","",f"Data: {today()}"]
        for line in lines:
            pdf.drawString(50,y,line[:110]); y-=24
            if y<60: pdf.showPage(); pdf.setFont(font,11); y=H-60
        pdf.save(); messagebox.showinfo("PDF",f"PDF salvo em:\n{path}")
        if sys.platform.startswith("win"):
            try: os.startfile(path)
            except Exception: pass
        elif sys.platform=="darwin": subprocess.Popen(["open",path])
        else:
            try: subprocess.Popen(["xdg-open",path])
            except Exception: pass

    # ---------------- AVALIAÇÕES ----------------
    def avaliacoes(self):
        self.clear(); self.header("⭐ Avaliações","Comentários dos clientes sobre os imóveis.",("＋ Nova avaliação",self.new_review))
        box=ctk.CTkScrollableFrame(self.area,fg_color=CARD,corner_radius=16); box.pack(fill="both",expand=True)
        c=db(); rows=c.execute("""SELECT a.*,c.nome cliente,i.titulo imovel FROM avaliacoes a
          LEFT JOIN clientes c ON c.id=a.cliente_id LEFT JOIN imoveis i ON i.id=a.imovel_id ORDER BY a.id DESC""").fetchall(); c.close()
        if not rows: self.empty(box,"⭐\n\nNenhuma avaliação cadastrada."); return
        for r in rows:
            card=ctk.CTkFrame(box,corner_radius=14,fg_color=CARD2,border_width=1,border_color=BORDER); card.pack(fill="x",padx=8,pady=7)
            ctk.CTkLabel(card,text=f"{'★'*int(r['nota'])}   {r['imovel'] or 'Imóvel'}\n👤 {r['cliente'] or 'Cliente'}\n\n{r['comentario'] or '-'}",justify="left",anchor="w").pack(fill="x",padx=18,pady=15)

    def new_review(self):
        c=db(); clients=c.execute("SELECT id,nome FROM clientes ORDER BY nome").fetchall(); props=c.execute("SELECT id,titulo FROM imoveis ORDER BY titulo").fetchall(); c.close()
        if not clients or not props: messagebox.showwarning("Dados necessários","Cadastre clientes e imóveis primeiro."); return
        w=ctk.CTkToplevel(self); w.title("Nova avaliação"); w.geometry("540x570"); w.grab_set(); f=ctk.CTkScrollableFrame(w,fg_color="transparent"); f.pack(fill="both",expand=True); ctk.CTkLabel(f,text="⭐ Nova avaliação",font=ctk.CTkFont(size=25,weight="bold")).pack(pady=20)
        cd={f"{x['id']} - {x['nome']}":x['id'] for x in clients}; pd={f"{x['id']} - {x['titulo']}":x['id'] for x in props}
        def combo(label,vals): ctk.CTkLabel(f,text=label).pack(anchor="w",padx=30); b=ctk.CTkComboBox(f,values=vals,height=38); b.set(vals[0]); b.pack(fill="x",padx=30,pady=(3,10)); return b
        cb=combo("Cliente",list(cd)); pb=combo("Imóvel",list(pd)); rate=combo("Nota",["1","2","3","4","5"]); rate.set("5")
        ctk.CTkLabel(f,text="Comentário").pack(anchor="w",padx=30); text=ctk.CTkTextbox(f,height=110); text.pack(fill="x",padx=30)
        def save():
            c=db(); c.execute("INSERT INTO avaliacoes(cliente_id,imovel_id,nota,comentario,criado_em) VALUES(?,?,?,?,?)",(cd[cb.get()],pd[pb.get()],int(rate.get()),text.get("1.0","end").strip(),now())); c.commit(); c.close(); w.destroy(); self.avaliacoes()
        ctk.CTkButton(f,text="⭐ Salvar avaliação",height=45,command=save).pack(fill="x",padx=30,pady=20)

    # ---------------- VENDAS ----------------
    def vendas(self):
        self.clear(); self.header("📊 Vendas","Registre vendas e acompanhe o faturamento.",("＋ Registrar venda",self.new_sale))
        c=db(); rows=c.execute("""SELECT v.*,c.nome cliente,i.titulo imovel FROM vendas v
          LEFT JOIN clientes c ON c.id=v.cliente_id LEFT JOIN imoveis i ON i.id=v.imovel_id ORDER BY v.id DESC""").fetchall(); total=c.execute("SELECT COALESCE(SUM(valor),0) FROM vendas").fetchone()[0]; c.close()
        top=ctk.CTkFrame(self.area,fg_color=CARD,corner_radius=14,border_width=1,border_color=BORDER); top.pack(fill="x",pady=(0,12)); ctk.CTkLabel(top,text="💰 Total vendido",text_color=MUTED).pack(anchor="w",padx=18,pady=(13,2)); ctk.CTkLabel(top,text=money(total),font=ctk.CTkFont(size=25,weight="bold")).pack(anchor="w",padx=18,pady=(0,13))
        box=ctk.CTkScrollableFrame(self.area,fg_color=CARD,corner_radius=16); box.pack(fill="both",expand=True)
        if not rows: self.empty(box,"📊\n\nNenhuma venda registrada."); return
        for r in rows:
            card=ctk.CTkFrame(box,corner_radius=14,fg_color=CARD2,border_width=1,border_color=BORDER); card.pack(fill="x",padx=8,pady=7)
            ctk.CTkLabel(card,text=f"🏠 {r['imovel'] or 'Imóvel'}\n👤 {r['cliente'] or 'Cliente'}\n💰 {money(r['valor'])}\n📅 {r['data']}\n📝 {r['observacao'] or '-'}",justify="left",anchor="w").pack(fill="x",padx=18,pady=15)

    def new_sale(self):
        c=db(); clients=c.execute("SELECT id,nome FROM clientes ORDER BY nome").fetchall(); props=c.execute("SELECT id,titulo,valor FROM imoveis WHERE status!='Vendido' ORDER BY titulo").fetchall(); c.close()
        if not clients or not props: messagebox.showwarning("Dados necessários","Cadastre clientes e pelo menos um imóvel disponível."); return
        w=ctk.CTkToplevel(self); w.title("Registrar venda"); w.geometry("540x600"); w.grab_set(); f=ctk.CTkScrollableFrame(w,fg_color="transparent"); f.pack(fill="both",expand=True); ctk.CTkLabel(f,text="💰 Registrar venda",font=ctk.CTkFont(size=25,weight="bold")).pack(pady=20)
        cd={f"{x['id']} - {x['nome']}":x['id'] for x in clients}; pd={f"{x['id']} - {x['titulo']}":x for x in props}
        def combo(label,vals): ctk.CTkLabel(f,text=label).pack(anchor="w",padx=30); b=ctk.CTkComboBox(f,values=vals,height=38); b.set(vals[0]); b.pack(fill="x",padx=30,pady=(3,10)); return b
        cb=combo("Cliente",list(cd)); pb=combo("Imóvel",list(pd)); ctk.CTkLabel(f,text="Valor da venda").pack(anchor="w",padx=30); value=ctk.CTkEntry(f,height=38); value.insert(0,str(pd[pb.get()]["valor"])); value.pack(fill="x",padx=30,pady=(3,10)); pb.configure(command=lambda *_: (value.delete(0,"end"),value.insert(0,str(pd[pb.get()]["valor"]))))
        ctk.CTkLabel(f,text="Observação").pack(anchor="w",padx=30); obs=ctk.CTkTextbox(f,height=80); obs.pack(fill="x",padx=30)
        def save():
            try: val=number(value.get())
            except Exception: messagebox.showerror("Erro","Informe um valor válido."); return
            if val<=0: messagebox.showerror("Erro","O valor da venda deve ser maior que zero."); return
            pid=pd[pb.get()]["id"]; c=db(); c.execute("INSERT INTO vendas(cliente_id,imovel_id,valor,data,observacao) VALUES(?,?,?,?,?)",(cd[cb.get()],pid,val,today(),obs.get("1.0","end").strip())); c.execute("UPDATE imoveis SET status='Vendido' WHERE id=?",(pid,)); c.commit(); c.close(); w.destroy(); self.vendas()
        ctk.CTkButton(f,text="💾 Registrar venda",height=45,command=save).pack(fill="x",padx=30,pady=20)


if __name__ == "__main__":
    create_db()
    app=App()
    app.mainloop()
