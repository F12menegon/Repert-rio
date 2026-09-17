
import sqlite3
import os
from datetime import datetime
from tkinter import messagebox, filedialog

import customtkinter as ctk
from PIL import Image, ImageTk

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    Figure = None
    FigureCanvasTkAgg = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas
except ImportError:
    A4 = None
    pdf_canvas = None


# ============================================================
# CONFIGURAÇÃO
# ============================================================

DB = "imobiliaria.db"
PASTA_IMAGENS = "recursos/imagens"

os.makedirs(PASTA_IMAGENS, exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ============================================================
# BANCO DE DADOS
# ============================================================

def conectar():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def criar_banco():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
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
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            interesse TEXT DEFAULT '',
            observacao TEXT DEFAULT '',
            criado_em TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            imovel_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            observacao TEXT DEFAULT '',
            status TEXT DEFAULT 'Agendada',
            criado_em TEXT NOT NULL,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id),
            FOREIGN KEY(imovel_id) REFERENCES imoveis(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            imovel_id INTEGER NOT NULL,
            valor_imovel REAL DEFAULT 0,
            entrada REAL DEFAULT 0,
            desconto REAL DEFAULT 0,
            financiamento REAL DEFAULT 0,
            observacao TEXT DEFAULT '',
            criado_em TEXT NOT NULL,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id),
            FOREIGN KEY(imovel_id) REFERENCES imoveis(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            imovel_id INTEGER NOT NULL,
            nota INTEGER NOT NULL,
            comentario TEXT DEFAULT '',
            criado_em TEXT NOT NULL,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id),
            FOREIGN KEY(imovel_id) REFERENCES imoveis(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            imovel_id INTEGER NOT NULL,
            valor REAL NOT NULL,
            data TEXT NOT NULL,
            observacao TEXT DEFAULT '',
            FOREIGN KEY(cliente_id) REFERENCES clientes(id),
            FOREIGN KEY(imovel_id) REFERENCES imoveis(id)
        )
    """)
    conn.commit()
    conn.close()

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def moeda(valor):
    return (
        f"R$ {float(valor):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def numero(texto):
    texto = str(texto).strip()

    if not texto:
        return 0

    texto = texto.replace("R$", "").replace(" ", "")

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    return float(texto)


def hoje():
    return datetime.now().strftime("%d/%m/%Y")


def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")

# ============================================================
# APLICAÇÃO
# ============================================================

class SistemaImobiliario(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("🏠 Recem Imobiliário")
        self.geometry("1280x780")
        self.minsize(1100, 700)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.imagem_atual = None

        self.criar_menu()
        self.criar_area()

        self.dashboard()

    # ========================================================
    # MENU
    # ========================================================
    def criar_menu(self):

        self.menu = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0
        )

        self.menu.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        self.menu.grid_propagate(False)

        ctk.CTkLabel(
            self.menu,
            text="Recem Imóveis",
            font=ctk.CTkFont(
                size=23,
                weight="bold"
            )
        ).pack(pady=(30, 3))

        ctk.CTkLabel(
            self.menu,
            text="Sistema de Gestão",
            text_color="#9ca3af"
        ).pack(pady=(0, 25))

        botoes = [

            ("🏠  Dashboard", self.dashboard),

            ("🏡  Imóveis", self.imoveis),

            ("👥  Clientes", self.clientes),

            ("📅  Visitas", self.visitas),

            ("💰  Orçamentos", self.orcamentos),

            ("⭐  Avaliações", self.avaliacoes),

            ("📊  Vendas", self.vendas),

        ]

        for texto, comando in botoes:

            ctk.CTkButton(
                self.menu,
                text=texto,
                command=comando,
                height=43,
                corner_radius=10,
                fg_color="transparent",
                hover_color="#1f3b66",
                anchor="w",
                font=ctk.CTkFont(size=14)
            ).pack(
                fill="x",
                padx=18,
                pady=4
            )

        ctk.CTkLabel(
            self.menu,
            text=""
        ).pack(expand=True)

        ctk.CTkLabel(
            self.menu,
            text="Recem Imobiliário • V1",
            text_color="#6b7280"
        ).pack(pady=15)

    # ========================================================
    # ÁREA
    # ========================================================

    def criar_area(self):

        self.area = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.area.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=25,
            pady=22
        )

        self.area.grid_columnconfigure(
            0,
            weight=1
        )

    def limpar(self):

        for widget in self.area.winfo_children():
            widget.destroy()

    def cabecalho(self, titulo, descricao):

        frame = ctk.CTkFrame(
            self.area,
            fg_color="transparent"
        )

        frame.pack(
            fill="x",
            pady=(0, 20)
        )

        ctk.CTkLabel(
            frame,
            text=titulo,
            font=ctk.CTkFont(
                size=30,
                weight="bold"
            )
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame,
            text=descricao,
            text_color="#9ca3af"
        ).pack(anchor="w")

    def card(self, parent, titulo, valor, coluna):

        frame = ctk.CTkFrame(
            parent,
            corner_radius=16
        )

        frame.grid(
            row=0,
            column=coluna,
            sticky="nsew",
            padx=6
        )

        ctk.CTkLabel(
            frame,
            text=titulo,
            text_color="#9ca3af"
        ).pack(
            anchor="w",
            padx=18,
            pady=(16, 3)
        )

        ctk.CTkLabel(
            frame,
            text=valor,
            font=ctk.CTkFont(
                size=24,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=18,
            pady=(0, 16)
        )

    # ========================================================
    # DASHBOARD
    # ========================================================

    def dashboard(self):

        self.limpar()

        self.cabecalho(
            "Olá! 👋",
            "Resumo da sua imobiliária."
        )

        conn = conectar()

        imoveis = conn.execute(
            "SELECT COUNT(*) FROM imoveis"
        ).fetchone()[0]

        clientes = conn.execute(
            "SELECT COUNT(*) FROM clientes"
        ).fetchone()[0]

        visitas = conn.execute(
            "SELECT COUNT(*) FROM visitas WHERE status='Agendada'"
        ).fetchone()[0]

        vendas_total = conn.execute(
            "SELECT COALESCE(SUM(valor),0) FROM vendas"
        ).fetchone()[0]

        conn.close()

        resumo = ctk.CTkFrame(
            self.area,
            fg_color="transparent"
        )

        resumo.pack(fill="x")

        for i in range(4):
            resumo.grid_columnconfigure(
                i,
                weight=1
            )

        self.card(
            resumo,
            "🏡 Imóveis",
            str(imoveis),
            0
        )

        self.card(
            resumo,
            "👥 Clientes",
            str(clientes),
            1
        )

        self.card(
            resumo,
            "📅 Visitas",
            str(visitas),
            2
        )

        self.card(
            resumo,
            "💰 Vendas",
            moeda(vendas_total),
            3
        )

        baixo = ctk.CTkFrame(
            self.area,
            fg_color="transparent"
        )

        baixo.pack(
            fill="both",
            expand=True,
            pady=(20, 0)
        )

        baixo.grid_columnconfigure(
            0,
            weight=1
        )

        baixo.grid_columnconfigure(
            1,
            weight=1
        )

        baixo.grid_rowconfigure(
            0,
            weight=1
        )

        # GRÁFICO

        grafico = ctk.CTkFrame(
            baixo,
            corner_radius=16
        )

        grafico.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8)
        )

        ctk.CTkLabel(
            grafico,
            text="📊 Vendas",
            font=ctk.CTkFont(
                size=19,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 5)
        )

        if Figure:

            conn = conectar()

            dados = conn.execute("""
                SELECT substr(data,4,7) mes,
                       SUM(valor) total
                FROM vendas
                GROUP BY substr(data,4,7)
                ORDER BY id
                LIMIT 6
            """).fetchall()

            conn.close()

            fig = Figure(
                figsize=(5, 3),
                dpi=90
            )

            ax = fig.add_subplot(111)

            if dados:

                meses = [
                    d["mes"]
                    for d in dados
                ]

                valores = [
                    d["total"]
                    for d in dados
                ]

                ax.bar(
                    meses,
                    valores
                )

                ax.set_ylabel(
                    "Valor"
                )

                ax.tick_params(
                    axis="x",
                    rotation=30
                )

            else:

                ax.text(
                    0.5,
                    0.5,
                    "Nenhuma venda registrada",
                    ha="center",
                    va="center"
                )

                ax.set_xticks([])
                ax.set_yticks([])

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(
                fig,
                master=grafico
            )

            canvas.draw()

            canvas.get_tk_widget().pack(
                fill="both",
                expand=True,
                padx=10,
                pady=10
            )

        # PRÓXIMAS VISITAS

        agenda = ctk.CTkFrame(
            baixo,
            corner_radius=16
        )

        agenda.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(8, 0)
        )

        ctk.CTkLabel(
            agenda,
            text="📅 Próximas visitas",
            font=ctk.CTkFont(
                size=19,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        conn = conectar()

        visitas = conn.execute("""
            SELECT v.*, c.nome cliente,
                   i.titulo imovel
            FROM visitas v
            JOIN clientes c
            ON c.id=v.cliente_id
            JOIN imoveis i
            ON i.id=v.imovel_id
            WHERE v.status='Agendada'
            ORDER BY v.data,v.hora
            LIMIT 6
        """).fetchall()

        conn.close()

        if not visitas:

            ctk.CTkLabel(
                agenda,
                text="Nenhuma visita agendada.",
                text_color="#9ca3af"
            ).pack(
                anchor="w",
                padx=20,
                pady=20
            )

        else:

            for visita in visitas:

                ctk.CTkLabel(
                    agenda,
                    text=(
                        f"📅 {visita['data']} • "
                        f"{visita['hora']}\n"
                        f"👤 {visita['cliente']}\n"
                        f"🏠 {visita['imovel']}"
                    ),
                    justify="left",
                    anchor="w"
                ).pack(
                    fill="x",
                    padx=20,
                    pady=9
                )

    # ========================================================
    # IMÓVEIS
    # ========================================================

    def imoveis(self):

        self.limpar()

        self.cabecalho(
            "🏡 Imóveis",
            "Gerencie casas, apartamentos, sobrados e mansões."
        )

        barra = ctk.CTkFrame(
            self.area,
            fg_color="transparent"
        )

        barra.pack(
            fill="x"
        )

        self.busca_imovel = ctk.CTkEntry(
            barra,
            placeholder_text="🔎 Pesquisar imóvel...",
            height=40
        )

        self.busca_imovel.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 10)
        )

        self.filtro_tipo = ctk.CTkComboBox(
            barra,
            values=[
                "Todos",
                "Casa",
                "Apartamento",
                "Sobrado",
                "Mansão"
            ],
            width=170,
            height=40
        )

        self.filtro_tipo.set("Todos")

        self.filtro_tipo.pack(
            side="left",
            padx=5
        )

        ctk.CTkButton(
            barra,
            text="🔎 Buscar",
            height=40,
            command=self.carregar_imoveis
        ).pack(
            side="left",
            padx=5
        )

        ctk.CTkButton(
            barra,
            text="＋ Novo imóvel",
            height=40,
            command=self.novo_imovel
        ).pack(
            side="left",
            padx=5
        )

        self.lista_imoveis = ctk.CTkScrollableFrame(
            self.area,
            corner_radius=15
        )

        self.lista_imoveis.pack(
            fill="both",
            expand=True,
            pady=(15, 0)
        )

        self.carregar_imoveis()

    def carregar_imoveis(self):

        for widget in self.lista_imoveis.winfo_children():
            widget.destroy()

        busca = self.busca_imovel.get().strip()

        tipo = self.filtro_tipo.get()

        conn = conectar()

        sql = """
            SELECT * FROM imoveis
            WHERE (titulo LIKE ?
            OR local LIKE ?)
        """

        params = [
            f"%{busca}%",
            f"%{busca}%"
        ]

        if tipo != "Todos":

            sql += " AND tipo=?"

            params.append(tipo)

        sql += " ORDER BY id DESC"

        dados = conn.execute(
            sql,
            params
        ).fetchall()

        conn.close()

        if not dados:

            ctk.CTkLabel(
                self.lista_imoveis,
                text="🏠\n\nNenhum imóvel encontrado.",
                font=ctk.CTkFont(size=17),
                text_color="#9ca3af"
            ).pack(pady=80)

            return

        for imovel in dados:

            self.cartao_imovel(
                imovel
            )

    def cartao_imovel(self, imovel):

        card = ctk.CTkFrame(
            self.lista_imoveis,
            corner_radius=15
        )

        card.pack(
            fill="x",
            padx=5,
            pady=7
        )

        card.grid_columnconfigure(
            1,
            weight=1
        )

        # FOTO

        foto_frame = ctk.CTkFrame(
            card,
            width=150,
            height=110,
            corner_radius=10
        )

        foto_frame.grid(
            row=0,
            column=0,
            padx=15,
            pady=15
        )

        foto_frame.grid_propagate(False)

        if (
            imovel["imagem"]
            and os.path.exists(imovel["imagem"])
        ):

            try:

                imagem = Image.open(
                    imovel["imagem"]
                )

                imagem.thumbnail(
                    (140, 100)
                )

                foto = ImageTk.PhotoImage(
                    imagem
                )

                label = ctk.CTkLabel(
                    foto_frame,
                    text="",
                    image=foto
                )

                label.image = foto

                label.pack(
                    expand=True
                )

            except:
                pass

        else:

            ctk.CTkLabel(
                foto_frame,
                text="🏠",
                font=ctk.CTkFont(size=40)
            ).pack(
                expand=True
            )

        # INFORMAÇÕES

        info = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )

        info.grid(
            row=0,
            column=1,
            sticky="nsew",
            pady=15
        )

        favorito = "❤️" if imovel["favorito"] else "🤍"

        ctk.CTkLabel(
            info,
            text=f"{imovel['titulo']}   {favorito}",
            font=ctk.CTkFont(
                size=18,
                weight="bold"
            )
        ).pack(
            anchor="w"
        )

        ctk.CTkLabel(
            info,
            text=(
                f"{imovel['tipo']} • 📍 {imovel['local']}\n"
                f"🛏 {imovel['quartos']} • "
                f"🚿 {imovel['banheiros']} • "
                f"🚗 {imovel['vagas']} • "
                f"📐 {imovel['area']} m²"
            ),
            text_color="#aab3c2",
            justify="left"
        ).pack(
            anchor="w",
            pady=5
        )

        ctk.CTkLabel(
            info,
            text=moeda(imovel["valor"]),
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            )
        ).pack(
            anchor="w"
        )

        # BOTÕES

        botoes = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )

        botoes.grid(
            row=0,
            column=2,
            padx=15
        )

        ctk.CTkButton(
            botoes,
            text="👁 Ver",
            width=100,
            command=lambda i=imovel["id"]:
                self.detalhes_imovel(i)
        ).pack(pady=3)

        ctk.CTkButton(
            botoes,
            text=favorito,
            width=100,
            command=lambda i=imovel["id"]:
                self.alternar_favorito(i)
        ).pack(pady=3)

        ctk.CTkButton(
            botoes,
            text="📅 Visita",
            width=100,
            command=lambda i=imovel["id"]:
                self.visita_para_imovel(i)
        ).pack(pady=3)

    def alternar_favorito(self, id_imovel):

        conn = conectar()

        atual = conn.execute(
            "SELECT favorito FROM imoveis WHERE id=?",
            (id_imovel,)
        ).fetchone()[0]

        conn.execute(
            "UPDATE imoveis SET favorito=? WHERE id=?",
            (0 if atual else 1, id_imovel)
        )

        conn.commit()
        conn.close()

        self.carregar_imoveis()

    def novo_imovel(self):

        janela = ctk.CTkToplevel(self)

        janela.title("Novo imóvel")
        janela.geometry("540x720")
        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="🏡 Cadastrar imóvel",
            font=ctk.CTkFont(
                size=25,
                weight="bold"
            )
        ).pack(pady=20)

        campos = {}

        def campo(nome, placeholder):

            ctk.CTkLabel(
                janela,
                text=nome
            ).pack(
                anchor="w",
                padx=35,
                pady=(5, 2)
            )

            entrada = ctk.CTkEntry(
                janela,
                placeholder_text=placeholder,
                height=36
            )

            entrada.pack(
                fill="x",
                padx=35
            )

            campos[nome] = entrada

        campo(
            "Título",
            "Ex.: Casa moderna no Centro"
        )

        campo(
            "Localização",
            "Ex.: São Paulo - SP"
        )

        ctk.CTkLabel(
            janela,
            text="Tipo"
        ).pack(
            anchor="w",
            padx=35,
            pady=(5, 2)
        )

        tipo = ctk.CTkComboBox(
            janela,
            values=[
                "Casa",
                "Apartamento",
                "Sobrado",
                "Mansão"
            ],
            height=36
        )

        tipo.set("Casa")

        tipo.pack(
            fill="x",
            padx=35
        )

        campo(
            "Quartos",
            "3"
        )

        campo(
            "Banheiros",
            "2"
        )

        campo(
            "Vagas",
            "2"
        )

        campo(
            "Área",
            "120"
        )

        campo(
            "Valor",
            "750000"
        )

        ctk.CTkLabel(
            janela,
            text="Descrição"
        ).pack(
            anchor="w",
            padx=35,
            pady=(5, 2)
        )

        descricao = ctk.CTkTextbox(
            janela,
            height=80
        )

        descricao.pack(
            fill="x",
            padx=35
        )

        imagem = {"path": ""}

        def escolher_imagem():

            caminho = filedialog.askopenfilename(
                filetypes=[
                    (
                        "Imagens",
                        "*.png *.jpg *.jpeg"
                    )
                ]
            )

            if caminho:

                imagem["path"] = caminho

                botao_imagem.configure(
                    text="✅ Imagem selecionada"
                )

        botao_imagem = ctk.CTkButton(
            janela,
            text="🖼 Escolher foto",
            command=escolher_imagem
        )

        botao_imagem.pack(
            fill="x",
            padx=35,
            pady=10
        )

        def salvar():

            try:

                titulo = campos["Título"].get().strip()

                local = campos["Localização"].get().strip()

                if not titulo or not local:

                    raise ValueError(
                        "Título e localização são obrigatórios."
                    )

                quartos = int(
                    campos["Quartos"].get() or 0
                )

                banheiros = int(
                    campos["Banheiros"].get() or 0
                )

                vagas = int(
                    campos["Vagas"].get() or 0
                )

                area = numero(
                    campos["Área"].get()
                )

                valor = numero(
                    campos["Valor"].get()
                )

                conn = conectar()

                conn.execute("""
                    INSERT INTO imoveis
                    (
                        titulo,
                        tipo,
                        local,
                        quartos,
                        banheiros,
                        vagas,
                        area,
                        valor,
                        descricao,
                        imagem,
                        criado_em
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    titulo,
                    tipo.get(),
                    local,
                    quartos,
                    banheiros,
                    vagas,
                    area,
                    valor,
                    descricao.get(
                        "1.0",
                        "end"
                    ).strip(),
                    imagem["path"],
                    agora()
                ))

                conn.commit()
                conn.close()

                janela.destroy()

                self.imoveis()

                messagebox.showinfo(
                    "Sucesso",
                    "Imóvel cadastrado!"
                )

            except Exception as erro:

                messagebox.showerror(
                    "Erro",
                    str(erro)
                )

        ctk.CTkButton(
            janela,
            text="💾 Salvar imóvel",
            height=45,
            command=salvar
        ).pack(
            fill="x",
            padx=35,
            pady=10
        )

    def detalhes_imovel(self, id_imovel):

        conn = conectar()

        imovel = conn.execute(
            "SELECT * FROM imoveis WHERE id=?",
            (id_imovel,)
        ).fetchone()

        avaliacoes = conn.execute("""
            SELECT a.*, c.nome
            FROM avaliacoes a
            JOIN clientes c
            ON c.id=a.cliente_id
            WHERE a.imovel_id=?
            ORDER BY a.id DESC
        """, (id_imovel,)).fetchall()

        conn.close()

        janela = ctk.CTkToplevel(self)

        janela.title(
            f"Imóvel • {imovel['titulo']}"
        )

        janela.geometry(
            "700x700"
        )

        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text=imovel["titulo"],
            font=ctk.CTkFont(
                size=26,
                weight="bold"
            )
        ).pack(
            pady=(25, 5)
        )

        ctk.CTkLabel(
            janela,
            text=(
                f"{imovel['tipo']} • "
                f"📍 {imovel['local']}\n"
                f"🛏 {imovel['quartos']} quartos • "
                f"🚿 {imovel['banheiros']} banheiros • "
                f"🚗 {imovel['vagas']} vagas\n"
                f"📐 {imovel['area']} m²"
            ),
            justify="center",
            text_color="#aab3c2"
        ).pack()

        ctk.CTkLabel(
            janela,
            text=moeda(imovel["valor"]),
            font=ctk.CTkFont(
                size=22,
                weight="bold"
            )
        ).pack(
            pady=12
        )

        ctk.CTkLabel(
            janela,
            text=imovel["descricao"] or "Sem descrição.",
            wraplength=620,
            justify="left"
        ).pack(
            padx=30,
            pady=10
        )

        ctk.CTkLabel(
            janela,
            text="⭐ Avaliações e comentários",
            font=ctk.CTkFont(
                size=19,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=30,
            pady=(20, 8)
        )

        lista = ctk.CTkScrollableFrame(
            janela,
            height=220
        )

        lista.pack(
            fill="both",
            expand=True,
            padx=30
        )

        if not avaliacoes:

            ctk.CTkLabel(
                lista,
                text="Nenhuma avaliação ainda.",
                text_color="#9ca3af"
            ).pack(
                pady=30
            )

        else:

            for avaliacao in avaliacoes:

                estrelas = "★" * avaliacao["nota"]

                ctk.CTkLabel(
                    lista,
                    text=(
                        f"{estrelas}  •  "
                        f"{avaliacao['nome']}\n"
                        f"“{avaliacao['comentario']}”"
                    ),
                    justify="left",
                    anchor="w"
                ).pack(
                    fill="x",
                    pady=8
                )

    def visita_para_imovel(self, id_imovel):

        self.visitas(
            imovel_selecionado=id_imovel
        )

    # ========================================================
    # CLIENTES
    # ========================================================

    def clientes(self):

        self.limpar()

        self.cabecalho(
            "👥 Clientes",
            "Gerencie seus clientes e seus interesses."
        )

        barra = ctk.CTkFrame(
            self.area,
            fg_color="transparent"
        )

        barra.pack(
            fill="x"
        )

        ctk.CTkButton(
            barra,
            text="＋ Novo cliente",
            height=40,
            command=self.novo_cliente
        ).pack(
            side="right"
        )

        self.lista_clientes = ctk.CTkScrollableFrame(
            self.area,
            corner_radius=15
        )

        self.lista_clientes.pack(
            fill="both",
            expand=True,
            pady=(15, 0)
        )

        conn = conectar()

        dados = conn.execute(
            "SELECT * FROM clientes ORDER BY id DESC"
        ).fetchall()

        conn.close()

        if not dados:

            ctk.CTkLabel(
                self.lista_clientes,
                text="👥\n\nNenhum cliente cadastrado.",
                font=ctk.CTkFont(size=17),
                text_color="#9ca3af"
            ).pack(
                pady=80
            )

            return

        for cliente in dados:

            card = ctk.CTkFrame(
                self.lista_clientes,
                corner_radius=14
            )

            card.pack(
                fill="x",
                padx=5,
                pady=7
            )

            card.grid_columnconfigure(
                0,
                weight=1
            )

            info = ctk.CTkFrame(
                card,
                fg_color="transparent"
            )

            info.grid(
                row=0,
                column=0,
                sticky="ew",
                padx=18,
                pady=15
            )

            ctk.CTkLabel(
                info,
                text=f"👤 {cliente['nome']}",
                font=ctk.CTkFont(
                    size=18,
                    weight="bold"
                )
            ).pack(
                anchor="w"
            )

            ctk.CTkLabel(
                info,
                text=(
                    f"📞 {cliente['telefone'] or '-'}   "
                    f"✉️ {cliente['email'] or '-'}\n"
                    f"🏠 Interesse: "
                    f"{cliente['interesse'] or '-'}"
                ),
                text_color="#aab3c2",
                justify="left"
            ).pack(
                anchor="w",
                pady=5
            )

            ctk.CTkButton(
                card,
                text="🗑 Excluir",
                width=100,
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                command=lambda i=cliente["id"]:
                    self.excluir_cliente(i)
            ).grid(
                row=0,
                column=1,
                padx=15
            )

    def novo_cliente(self):

        janela = ctk.CTkToplevel(self)

        janela.title(
            "Novo cliente"
        )

        janela.geometry(
            "500x570"
        )

        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="👤 Novo cliente",
            font=ctk.CTkFont(
                size=25,
                weight="bold"
            )
        ).pack(
            pady=25
        )

        campos = {}

        for nome, placeholder in [

            ("Nome", "Nome completo"),

            ("Telefone", "(11) 99999-9999"),

            ("E-mail", "cliente@email.com"),

        ]:

            ctk.CTkLabel(
                janela,
                text=nome
            ).pack(
                anchor="w",
                padx=35
            )

            entrada = ctk.CTkEntry(
                janela,
                placeholder_text=placeholder,
                height=38
            )

            entrada.pack(
                fill="x",
                padx=35,
                pady=(3, 10)
            )

            campos[nome] = entrada

        ctk.CTkLabel(
            janela,
            text="Interesse"
        ).pack(
            anchor="w",
            padx=35
        )

        interesse = ctk.CTkComboBox(
            janela,
            values=[
                "Casa",
                "Apartamento",
                "Sobrado",
                "Mansão",
                "Não definido"
            ],
            height=38
        )

        interesse.set(
            "Não definido"
        )

        interesse.pack(
            fill="x",
            padx=35,
            pady=(3, 10)
        )

        ctk.CTkLabel(
            janela,
            text="Observação"
        ).pack(
            anchor="w",
            padx=35
        )

        observacao = ctk.CTkTextbox(
            janela,
            height=80
        )

        observacao.pack(
            fill="x",
            padx=35
        )

        def salvar():

            nome = campos["Nome"].get().strip()

            if not nome:

                messagebox.showerror(
                    "Erro",
                    "Informe o nome."
                )

                return

            conn = conectar()

            conn.execute("""
                INSERT INTO clientes
                (
                    nome,
                    telefone,
                    email,
                    interesse,
                    observacao,
                    criado_em
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                nome,
                campos["Telefone"].get(),
                campos["E-mail"].get(),
                interesse.get(),
                observacao.get(
                    "1.0",
                    "end"
                ).strip(),
                agora()
            ))

            conn.commit()
            conn.close()

            janela.destroy()

            self.clientes()

            messagebox.showinfo(
                "Sucesso",
                "Cliente cadastrado!"
            )

        ctk.CTkButton(
            janela,
            text="💾 Salvar cliente",
            height=45,
            command=salvar
        ).pack(
            fill="x",
            padx=35,
            pady=25
        )

    def excluir_cliente(self, id_cliente):

        conn = conectar()

        quantidade = conn.execute(
            "SELECT COUNT(*) FROM visitas WHERE cliente_id=?",
            (id_cliente,)
        ).fetchone()[0]

        conn.close()

        if quantidade:

            messagebox.showwarning(
                "Cliente em uso",
                "Esse cliente possui visitas cadastradas."
            )

            return

        if not messagebox.askyesno(
            "Confirmar",
            "Deseja excluir este cliente?"
        ):
            return

        conn = conectar()

        conn.execute(
            "DELETE FROM clientes WHERE id=?",
            (id_cliente,)
        )

        conn.commit()
        conn.close()

        self.clientes()

    # ========================================================
    # VISITAS
    # ========================================================

    def visitas(self, imovel_selecionado=None):

        self.limpar()

        self.cabecalho(
            "📅 Visitas agendadas",
            "Organize seus compromissos com clientes."
        )

        barra = ctk.CTkFrame(
            self.area,
            fg_color="transparent"
        )

        barra.pack(
            fill="x"
        )

        ctk.CTkButton(
            barra,
            text="＋ Agendar visita",
            height=40,
            command=lambda:
                self.nova_visita(imovel_selecionado)
        ).pack(
            side="right"
        )

        lista = ctk.CTkScrollableFrame(
            self.area,
            corner_radius=15
        )

        lista.pack(
            fill="both",
            expand=True,
            pady=(15, 0)
        )

        conn = conectar()

        dados = conn.execute("""
            SELECT
                v.*,
                c.nome cliente,
                i.titulo imovel,
                i.local local_imovel
            FROM visitas v
            JOIN clientes c
            ON c.id=v.cliente_id
            JOIN imoveis i
            ON i.id=v.imovel_id
            ORDER BY v.data,v.hora
        """).fetchall()

        conn.close()

        if not dados:

            ctk.CTkLabel(
                lista,
                text="📅\n\nNenhuma visita cadastrada.",
                font=ctk.CTkFont(size=17),
                text_color="#9ca3af"
            ).pack(
                pady=80
            )

            return

        for visita in dados:

            card = ctk.CTkFrame(
                lista,
                corner_radius=14
            )

            card.pack(
                fill="x",
                padx=5,
                pady=7
            )

            card.grid_columnconfigure(
                0,
                weight=1
            )

            info = ctk.CTkFrame(
                card,
                fg_color="transparent"
            )

            info.grid(
                row=0,
                column=0,
                sticky="ew",
                padx=18,
                pady=15
            )

            ctk.CTkLabel(
                info,
                text=(
                    f"📅 {visita['data']} "
                    f"• ⏰ {visita['hora']}"
                ),
                font=ctk.CTkFont(
                    size=18,
                    weight="bold"
                )
            ).pack(
                anchor="w"
            )

            ctk.CTkLabel(
                info,
                text=(
                    f"👤 {visita['cliente']}\n"
                    f"🏠 {visita['imovel']}\n"
                    f"📍 {visita['local_imovel']}\n"
                    f"Status: {visita['status']}"
                ),
                text_color="#aab3c2",
                justify="left"
            ).pack(
                anchor="w",
                pady=5
            )

            botoes = ctk.CTkFrame(
                card,
                fg_color="transparent"
            )

            botoes.grid(
                row=0,
                column=1,
                padx=15
            )

            if visita["status"] == "Agendada":

                ctk.CTkButton(
                    botoes,
                    text="✅ Concluir",
                    width=105,
                    command=lambda i=visita["id"]:
                        self.status_visita(
                            i,
                            "Concluída"
                        )
                ).pack(
                    pady=3
                )

                ctk.CTkButton(
                    botoes,
                    text="❌ Cancelar",
                    width=105,
                    fg_color="#7f1d1d",
                    hover_color="#991b1b",
                    command=lambda i=visita["id"]:
                        self.status_visita(
                            i,
                            "Cancelada"
                        )
                ).pack(
                    pady=3
                )

    def nova_visita(self, imovel_selecionado=None):

        conn = conectar()

        clientes = conn.execute(
            "SELECT id,nome FROM clientes ORDER BY nome"
        ).fetchall()

        imoveis = conn.execute(
            "SELECT id,titulo FROM imoveis ORDER BY titulo"
        ).fetchall()

        conn.close()

        if not clientes:

            messagebox.showwarning(
                "Cliente necessário",
                "Cadastre um cliente primeiro."
            )

            self.clientes()

            return

        if not imoveis:

            messagebox.showwarning(
                "Imóvel necessário",
                "Cadastre um imóvel primeiro."
            )

            self.imoveis()

            return

        janela = ctk.CTkToplevel(self)

        janela.title(
            "Agendar visita"
        )

        janela.geometry(
            "520x620"
        )

        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="📅 Agendar visita",
            font=ctk.CTkFont(
                size=25,
                weight="bold"
            )
        ).pack(
            pady=25
        )

        clientes_dict = {
            f"{c['id']} - {c['nome']}":
            c["id"]
            for c in clientes
        }

        ctk.CTkLabel(
            janela,
            text="Cliente"
        ).pack(
            anchor="w",
            padx=35
        )

        cliente_box = ctk.CTkComboBox(
            janela,
            values=list(
                clientes_dict.keys()
            ),
            height=38
        )

        cliente_box.set(
            list(clientes_dict.keys())[0]
        )

        cliente_box.pack(
            fill="x",
            padx=35,
            pady=(3, 10)
        )

        imoveis_dict = {
            f"{i['id']} - {i['titulo']}":
            i["id"]
            for i in imoveis
        }

        ctk.CTkLabel(
            janela,
            text="Imóvel"
        ).pack(
            anchor="w",
            padx=35
        )

        imovel_box = ctk.CTkComboBox(
            janela,
            values=list(
                imoveis_dict.keys()
            ),
            height=38
        )

        escolhido = list(
            imoveis_dict.keys()
        )[0]

        if imovel_selecionado:

            for texto, id_ in imoveis_dict.items():

                if id_ == imovel_selecionado:

                    escolhido = texto
                    break

        imovel_box.set(
            escolhido
        )

        imovel_box.pack(
            fill="x",
            padx=35,
            pady=(3, 10)
        )

        def campo(nome, placeholder):

            ctk.CTkLabel(
                janela,
                text=nome
            ).pack(
                anchor="w",
                padx=35
            )

            entrada = ctk.CTkEntry(
                janela,
                placeholder_text=placeholder,
                height=38
            )

            entrada.pack(
                fill="x",
                padx=35,
                pady=(3, 10)
            )

            return entrada

        data = campo(
            "Data",
            "DD/MM/AAAA"
        )

        hora = campo(
            "Hora",
            "HH:MM"
        )

        ctk.CTkLabel(
            janela,
            text="Observação"
        ).pack(
            anchor="w",
            padx=35
        )

        observacao = ctk.CTkTextbox(
            janela,
            height=70
        )

        observacao.pack(
            fill="x",
            padx=35
        )

        def salvar():

            try:

                data_txt = data.get().strip()

                hora_txt = hora.get().strip()

                datetime.strptime(
                    data_txt,
                    "%d/%m/%Y"
                )

                datetime.strptime(
                    hora_txt,
                    "%H:%M"
                )

                conn = conectar()

                conn.execute("""
                    INSERT INTO visitas
                    (
                        cliente_id,
                        imovel_id,
                        data,
                        hora,
                        observacao,
                        status,
                        criado_em
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    clientes_dict[
                        cliente_box.get()
                    ],
                    imoveis_dict[
                        imovel_box.get()
                    ],
                    data_txt,
                    hora_txt,
                    observacao.get(
                        "1.0",
                        "end"
                    ).strip(),
                    "Agendada",
                    agora()
                ))

                conn.commit()
                conn.close()

                janela.destroy()

                self.visitas()

                messagebox.showinfo(
                    "Sucesso",
                    "Visita agendada!"
                )

            except ValueError:

                messagebox.showerror(
                    "Erro",
                    "Use DD/MM/AAAA e HH:MM."
                )

        ctk.CTkButton(
            janela,
            text="📅 Agendar",
            height=45,
            command=salvar
        ).pack(
            fill="x",
            padx=35,
            pady=20
        )

    def status_visita(
        self,
        id_visita,
        status
    ):

        conn = conectar()

        conn.execute(
            "UPDATE visitas SET status=? WHERE id=?",
            (status, id_visita)
        )

        conn.commit()
        conn.close()

        self.visitas()

    # ========================================================
    # ORÇAMENTOS
    # ========================================================

    def orcamentos(self):

        self.limpar()

        self.cabecalho(
            "💰 Orçamentos",
            "Crie propostas para seus clientes."
        )

        ctk.CTkButton(
            self.area,
            text="＋ Novo orçamento",
            height=40,
            command=self.novo_orcamento
        ).pack(
            anchor="e"
        )

        lista = ctk.CTkScrollableFrame(
            self.area
        )

        lista.pack(
            fill="both",
            expand=True,
            pady=15
        )

        conn = conectar()

        dados = conn.execute("""
            SELECT
                o.*,
                c.nome cliente,
                i.titulo imovel
            FROM orcamentos o
            JOIN clientes c
            ON c.id=o.cliente_id
            JOIN imoveis i
            ON i.id=o.imovel_id
            ORDER BY o.id DESC
        """).fetchall()

        conn.close()

        if not dados:

            ctk.CTkLabel(
                lista,
                text="💰\n\nNenhum orçamento criado.",
                text_color="#9ca3af"
            ).pack(
                pady=80
            )

            return

        for o in dados:

            card = ctk.CTkFrame(
                lista,
                corner_radius=14
            )

            card.pack(
                fill="x",
                pady=7,
                padx=5
            )

            ctk.CTkLabel(
                card,
                text=(
                    f"👤 {o['cliente']}\n"
                    f"🏠 {o['imovel']}\n"
                    f"💰 Imóvel: {moeda(o['valor_imovel'])}\n"
                    f"Entrada: {moeda(o['entrada'])}   "
                    f"Desconto: {moeda(o['desconto'])}\n"
                    f"Financiamento: "
                    f"{moeda(o['financiamento'])}"
                ),
                justify="left"
            ).pack(
                anchor="w",
                padx=20,
                pady=15
            )

            ctk.CTkButton(
                card,
                text="📄 Gerar PDF",
                command=lambda i=o["id"]:
                    self.pdf_orcamento(i)
            ).pack(
                anchor="e",
                padx=20,
                pady=(0, 15)
            )

    def novo_orcamento(self):

        conn = conectar()

        clientes = conn.execute(
            "SELECT id,nome FROM clientes ORDER BY nome"
        ).fetchall()

        imoveis = conn.execute(
            "SELECT id,titulo,valor FROM imoveis ORDER BY titulo"
        ).fetchall()

        conn.close()

        if not clientes or not imoveis:

            messagebox.showwarning(
                "Dados necessários",
                "Cadastre pelo menos um cliente e um imóvel."
            )

            return

        janela = ctk.CTkToplevel(self)

        janela.title(
            "Novo orçamento"
        )

        janela.geometry(
            "540x650"
        )

        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="💰 Novo orçamento",
            font=ctk.CTkFont(
                size=25,
                weight="bold"
            )
        ).pack(
            pady=25
        )

        clientes_dict = {
            f"{c['id']} - {c['nome']}":
            c["id"]
            for c in clientes
        }

        imoveis_dict = {
            f"{i['id']} - {i['titulo']}":
            i
            for i in imoveis
        }

        def combo(nome, valores):

            ctk.CTkLabel(
                janela,
                text=nome
            ).pack(
                anchor="w",
                padx=35
            )

            box = ctk.CTkComboBox(
                janela,
                values=valores,
                height=38
            )

            box.set(
                valores[0]
            )

            box.pack(
                fill="x",
                padx=35,
                pady=(3, 10)
            )

            return box

        cliente_box = combo(
            "Cliente",
            list(clientes_dict.keys())
        )

        imovel_box = combo(
            "Imóvel",
            list(imoveis_dict.keys())
        )

        def campo(nome, valor=""):

            ctk.CTkLabel(
                janela,
                text=nome
            ).pack(
                anchor="w",
                padx=35
            )

            entrada = ctk.CTkEntry(
                janela,
                height=38
            )

            entrada.insert(
                0,
                valor
            )

            entrada.pack(
                fill="x",
                padx=35,
                pady=(3, 10)
            )

            return entrada

        valor = campo(
            "Valor do imóvel",
            str(
                imoveis_dict[
                    imovel_box.get()
                ]["valor"]
            )
        )

        entrada = campo(
            "Entrada",
            "0"
        )

        desconto = campo(
            "Desconto",
            "0"
        )

        financiamento = campo(
            "Financiamento",
            "0"
        )

        def atualizar_valor(event=None):

            item = imoveis_dict[
                imovel_box.get()
            ]

            valor.delete(
                0,
                "end"
            )

            valor.insert(
                0,
                str(item["valor"])
            )

        imovel_box.configure(
            command=atualizar_valor
        )

        ctk.CTkLabel(
            janela,
            text="Observação"
        ).pack(
            anchor="w",
            padx=35
        )

        obs = ctk.CTkTextbox(
            janela,
            height=70
        )

        obs.pack(
            fill="x",
            padx=35
        )

        def salvar():

            try:

                valor_imovel = numero(
                    valor.get()
                )

                entrada_v = numero(
                    entrada.get()
                )

                desconto_v = numero(
                    desconto.get()
                )

                financiamento_v = numero(
                    financiamento.get()
                )

                conn = conectar()

                conn.execute("""
                    INSERT INTO orcamentos
                    (
                        cliente_id,
                        imovel_id,
                        valor_imovel,
                        entrada,
                        desconto,
                        financiamento,
                        observacao,
                        criado_em
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clientes_dict[
                        cliente_box.get()
                    ],
                    imoveis_dict[
                        imovel_box.get()
                    ]["id"],
                    valor_imovel,
                    entrada_v,
                    desconto_v,
                    financiamento_v,
                    obs.get(
                        "1.0",
                        "end"
                    ).strip(),
                    agora()
                ))

                conn.commit()
                conn.close()

                janela.destroy()

                self.orcamentos()

                messagebox.showinfo(
                    "Sucesso",
                    "Orçamento criado!"
                )

            except Exception as erro:

                messagebox.showerror(
                    "Erro",
                    str(erro)
                )

        ctk.CTkButton(
            janela,
            text="💾 Salvar orçamento",
            height=45,
            command=salvar
        ).pack(
            fill="x",
            padx=35,
            pady=20
        )

    # ========================================================
    # PDF
    # ========================================================

    def pdf_orcamento(self, id_orcamento):

        if not pdf_canvas:

            messagebox.showerror(
                "Biblioteca ausente",
                "Instale reportlab."
            )

            return

        conn = conectar()

        o = conn.execute("""
            SELECT
                o.*,
                c.nome cliente,
                c.telefone,
                c.email,
                i.titulo imovel,
                i.local
            FROM orcamentos o
            JOIN clientes c
            ON c.id=o.cliente_id
            JOIN imoveis i
            ON i.id=o.imovel_id
            WHERE o.id=?
        """, (id_orcamento,)).fetchone()

        conn.close()

        caminho = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[
                ("PDF", "*.pdf")
            ],
            initialfile="orcamento_imobiliario.pdf"
        )

        if not caminho:
            return

        pdf = pdf_canvas.Canvas(
            caminho,
            pagesize=A4
        )

        largura, altura = A4

        pdf.setFont(
            "Helvetica-Bold",
            22
        )

        pdf.drawString(
            50,
            altura - 60,
            "ORÇAMENTO IMOBILIÁRIO"
        )

        pdf.setFont(
            "Helvetica",
            12
        )

        y = altura - 110

        linhas = [

            f"Cliente: {o['cliente']}",

            f"Telefone: {o['telefone']}",

            f"E-mail: {o['email']}",

            "",

            f"Imóvel: {o['imovel']}",

            f"Localização: {o['local']}",

            "",

            f"Valor do imóvel: {moeda(o['valor_imovel'])}",

            f"Entrada: {moeda(o['entrada'])}",

            f"Desconto: {moeda(o['desconto'])}",

            f"Financiamento: {moeda(o['financiamento'])}",

            "",

            f"Observação: {o['observacao']}",

            "",

            f"Data: {hoje()}"

        ]

        for linha in linhas:

            pdf.drawString(
                50,
                y,
                linha
            )

            y -= 25

        pdf.save()

        messagebox.showinfo(
            "PDF",
            "Orçamento gerado com sucesso!"
        )

    # ========================================================
    # AVALIAÇÕES
    # ========================================================

    def avaliacoes(self):

        self.limpar()

        self.cabecalho(
            "⭐ Avaliações",
            "Veja a opinião dos clientes sobre seus imóveis."
        )

        ctk.CTkButton(
            self.area,
            text="＋ Nova avaliação",
            height=40,
            command=self.nova_avaliacao
        ).pack(
            anchor="e"
        )

        lista = ctk.CTkScrollableFrame(
            self.area
        )

        lista.pack(
            fill="both",
            expand=True,
            pady=15
        )

        conn = conectar()

        dados = conn.execute("""
            SELECT
                a.*,
                c.nome cliente,
                i.titulo imovel
            FROM avaliacoes a
            JOIN clientes c
            ON c.id=a.cliente_id
            JOIN imoveis i
            ON i.id=a.imovel_id
            ORDER BY a.id DESC
        """).fetchall()

        conn.close()

        if not dados:

            ctk.CTkLabel(
                lista,
                text="⭐\n\nNenhuma avaliação cadastrada.",
                text_color="#9ca3af"
            ).pack(
                pady=80
            )

            return

        for a in dados:

            estrelas = "★" * a["nota"]

            card = ctk.CTkFrame(
                lista,
                corner_radius=14
            )

            card.pack(
                fill="x",
                padx=5,
                pady=7
            )

            ctk.CTkLabel(
                card,
                text=(
                    f"{estrelas}   {a['imovel']}\n"
                    f"👤 {a['cliente']}\n\n"
                    f"“{a['comentario']}”"
                ),
                justify="left",
                anchor="w"
            ).pack(
                fill="x",
                padx=20,
                pady=15
            )

    def nova_avaliacao(self):

        conn = conectar()

        clientes = conn.execute(
            "SELECT id,nome FROM clientes ORDER BY nome"
        ).fetchall()

        imoveis = conn.execute(
            "SELECT id,titulo FROM imoveis ORDER BY titulo"
        ).fetchall()

        conn.close()

        if not clientes or not imoveis:

            messagebox.showwarning(
                "Dados necessários",
                "Cadastre clientes e imóveis primeiro."
            )

            return

        janela = ctk.CTkToplevel(self)

        janela.title(
            "Nova avaliação"
        )

        janela.geometry(
            "520x530"
        )

        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="⭐ Nova avaliação",
            font=ctk.CTkFont(
                size=25,
                weight="bold"
            )
        ).pack(
            pady=25
        )

        clientes_dict = {
            f"{c['id']} - {c['nome']}":
            c["id"]
            for c in clientes
        }

        imoveis_dict = {
            f"{i['id']} - {i['titulo']}":
            i["id"]
            for i in imoveis
        }

        def combo(nome, valores):

            ctk.CTkLabel(
                janela,
                text=nome
            ).pack(
                anchor="w",
                padx=35
            )

            box = ctk.CTkComboBox(
                janela,
                values=valores,
                height=38
            )

            box.set(
                valores[0]
            )

            box.pack(
                fill="x",
                padx=35,
                pady=(3, 10)
            )

            return box

        cliente = combo(
            "Cliente",
            list(clientes_dict.keys())
        )

        imovel = combo(
            "Imóvel",
            list(imoveis_dict.keys())
        )

        ctk.CTkLabel(
            janela,
            text="Nota"
        ).pack(
            anchor="w",
            padx=35
        )

        nota = ctk.CTkComboBox(
            janela,
            values=[
                "1",
                "2",
                "3",
                "4",
                "5"
            ],
            height=38
        )

        nota.set("5")

        nota.pack(
            fill="x",
            padx=35,
            pady=(3, 10)
        )

        ctk.CTkLabel(
            janela,
            text="Comentário"
        ).pack(
            anchor="w",
            padx=35
        )

        comentario = ctk.CTkTextbox(
            janela,
            height=100
        )

        comentario.pack(
            fill="x",
            padx=35
        )

        def salvar():

            conn = conectar()

            conn.execute("""
                INSERT INTO avaliacoes
                (
                    cliente_id,
                    imovel_id,
                    nota,
                    comentario,
                    criado_em
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                clientes_dict[
                    cliente.get()
                ],
                imoveis_dict[
                    imovel.get()
                ],
                int(nota.get()),
                comentario.get(
                    "1.0",
                    "end"
                ).strip(),
                agora()
            ))

            conn.commit()
            conn.close()

            janela.destroy()

            self.avaliacoes()

            messagebox.showinfo(
                "Sucesso",
                "Avaliação cadastrada!"
            )

        ctk.CTkButton(
            janela,
            text="⭐ Salvar avaliação",
            height=45,
            command=salvar
        ).pack(
            fill="x",
            padx=35,
            pady=25
        )

    # ========================================================
    # VENDAS
    # ========================================================

    def vendas(self):

        self.limpar()

        self.cabecalho(
            "📊 Vendas",
            "Registre vendas e acompanhe os resultados."
        )

        ctk.CTkButton(
            self.area,
            text="＋ Registrar venda",
            height=40,
            command=self.nova_venda
        ).pack(
            anchor="e"
        )

        lista = ctk.CTkScrollableFrame(
            self.area
        )

        lista.pack(
            fill="both",
            expand=True,
            pady=15
        )

        conn = conectar()

        dados = conn.execute("""
            SELECT
                v.*,
                c.nome cliente,
                i.titulo imovel
            FROM vendas v
            JOIN clientes c
            ON c.id=v.cliente_id
            JOIN imoveis i
            ON i.id=v.imovel_id
            ORDER BY v.id DESC
        """).fetchall()

        total = conn.execute(
            "SELECT COALESCE(SUM(valor),0) FROM vendas"
        ).fetchone()[0]

        conn.close()

        ctk.CTkLabel(
            lista,
            text=f"💰 Total vendido: {moeda(total)}",
            font=ctk.CTkFont(
                size=21,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=10,
            pady=15
        )

        if not dados:

            ctk.CTkLabel(
                lista,
                text="Nenhuma venda registrada.",
                text_color="#9ca3af"
            ).pack(
                pady=50
            )

            return

        for venda in dados:

            card = ctk.CTkFrame(
                lista,
                corner_radius=14
            )

            card.pack(
                fill="x",
                padx=5,
                pady=7
            )

            ctk.CTkLabel(
                card,
                text=(
                    f"🏠 {venda['imovel']}\n"
                    f"👤 {venda['cliente']}\n"
                    f"💰 {moeda(venda['valor'])}\n"
                    f"📅 {venda['data']}"
                ),
                justify="left"
            ).pack(
                anchor="w",
                padx=20,
                pady=15
            )

    def nova_venda(self):

        conn = conectar()

        clientes = conn.execute(
            "SELECT id,nome FROM clientes ORDER BY nome"
        ).fetchall()

        imoveis = conn.execute(
            "SELECT id,titulo,valor FROM imoveis ORDER BY titulo"
        ).fetchall()

        conn.close()

        if not clientes or not imoveis:

            messagebox.showwarning(
                "Dados necessários",
                "Cadastre clientes e imóveis primeiro."
            )

            return

        janela = ctk.CTkToplevel(self)

        janela.title(
            "Registrar venda"
        )

        janela.geometry(
            "520x520"
        )

        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="💰 Registrar venda",
            font=ctk.CTkFont(
                size=25,
                weight="bold"
            )
        ).pack(
            pady=25
        )

        clientes_dict = {
            f"{c['id']} - {c['nome']}":
            c["id"]
            for c in clientes
        }

        imoveis_dict = {
            f"{i['id']} - {i['titulo']}":
            i
            for i in imoveis
        }

        def combo(nome, valores):

            ctk.CTkLabel(
                janela,
                text=nome
            ).pack(
                anchor="w",
                padx=35
            )

            box = ctk.CTkComboBox(
                janela,
                values=valores,
                height=38
            )

            box.set(
                valores[0]
            )

            box.pack(
                fill="x",
                padx=35,
                pady=(3, 10)
            )

            return box

        cliente = combo(
            "Cliente",
            list(clientes_dict.keys())
        )

        imovel = combo(
            "Imóvel",
            list(imoveis_dict.keys())
        )

        ctk.CTkLabel(
            janela,
            text="Valor da venda"
        ).pack(
            anchor="w",
            padx=35
        )

        valor = ctk.CTkEntry(
            janela,
            height=38
        )

        valor.insert(
            0,
            str(
                imoveis_dict[
                    imovel.get()
                ]["valor"]
            )
        )

        valor.pack(
            fill="x",
            padx=35,
            pady=(3, 10)
        )

        def atualizar(event=None):

            item = imoveis_dict[
                imovel.get()
            ]

            valor.delete(
                0,
                "end"
            )

            valor.insert(
                0,
                str(item["valor"])
            )

        imovel.configure(
            command=atualizar
        )

        ctk.CTkLabel(
            janela,
            text="Observação"
        ).pack(
            anchor="w",
            padx=35
        )

        obs = ctk.CTkTextbox(
            janela,
            height=70
        )

        obs.pack(
            fill="x",
            padx=35
        )

        def salvar():

            try:

                valor_venda = numero(
                    valor.get()
                )

                conn = conectar()

                conn.execute("""
                    INSERT INTO vendas
                    (
                        cliente_id,
                        imovel_id,
                        valor,
                        data,
                        observacao
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    clientes_dict[
                        cliente.get()
                    ],
                    imoveis_dict[
                        imovel.get()
                    ]["id"],
                    valor_venda,
                    hoje(),
                    obs.get(
                        "1.0",
                        "end"
                    ).strip()
                ))

                conn.execute("""
                    UPDATE imoveis
                    SET status='Vendido'
                    WHERE id=?
                """, (
                    imoveis_dict[
                        imovel.get()
                    ]["id"],
                ))

                conn.commit()
                conn.close()

                janela.destroy()

                self.vendas()

                messagebox.showinfo(
                    "Sucesso",
                    "Venda registrada!"
                )

            except Exception as erro:

                messagebox.showerror(
                    "Erro",
                    str(erro)
                )

        ctk.CTkButton(
            janela,
            text="💾 Registrar venda",
            height=45,
            command=salvar
        ).pack(
            fill="x",
            padx=35,
            pady=25
        )

# ============================================================
# INICIAR
# ============================================================

if __name__ == "__main__":

    criar_banco()

    app = SistemaImobiliario()

    app.mainloop()