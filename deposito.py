import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkcalendar import DateEntry

class GerenciadorDeposito:
    def __init__(self, db_name: str = "deposito.db"):
        """Inicializa o gerenciador e cria as tabelas necessárias"""
        self.db_name = db_name
        self.criar_tabelas()
    
    def conectar(self) -> sqlite3.Connection:
        """Cria uma conexão com o banco de dados"""
        return sqlite3.connect(self.db_name)
    
    def criar_tabelas(self):
        """Cria as tabelas do banco de dados"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                categoria TEXT,
                quantidade INTEGER NOT NULL DEFAULT 0,
                localizacao TEXT,
                data_cadastro TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                data_movimentacao TEXT NOT NULL,
                observacao TEXT,
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def adicionar_produto(self, nome: str, quantidade: int = 0, 
                         descricao: str = "", categoria: str = "", 
                         localizacao: str = "") -> int:
        """Adiciona um novo produto ao depósito"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO produtos (nome, descricao, categoria, quantidade, localizacao, data_cadastro)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nome.upper(), descricao.upper(), categoria.upper(), quantidade, localizacao.upper(), data_atual))
        
        produto_id = cursor.lastrowid
        
        if quantidade > 0:
            cursor.execute("""
                INSERT INTO movimentacoes (produto_id, tipo, quantidade, data_movimentacao, observacao)
                VALUES (?, 'ENTRADA', ?, ?, 'Estoque inicial')
            """, (produto_id, quantidade, data_atual))
        
        conn.commit()
        conn.close()
        
        return produto_id
    
    def listar_produtos(self, categoria: Optional[str] = None) -> List[Tuple]:
        """Lista todos os produtos ou filtra por categoria"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        if categoria:
            cursor.execute("""
                SELECT id, nome, descricao, categoria, quantidade, localizacao
                FROM produtos WHERE categoria = ?
                ORDER BY nome
            """, (categoria,))
        else:
            cursor.execute("""
                SELECT id, nome, descricao, categoria, quantidade, localizacao
                FROM produtos ORDER BY nome
            """)
        
        produtos = cursor.fetchall()
        conn.close()
        
        return produtos
    
    def buscar_produto(self, produto_id: int) -> Optional[Tuple]:
        """Busca um produto específico pelo ID"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nome, descricao, categoria, quantidade, localizacao, data_cadastro
            FROM produtos WHERE id = ?
        """, (produto_id,))
        
        produto = cursor.fetchone()
        conn.close()
        
        return produto
    
    def buscar_produto_por_nome(self, nome: str) -> List[Tuple]:
        """Busca produtos por nome (busca parcial)"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nome, descricao, categoria, quantidade, localizacao
            FROM produtos WHERE nome LIKE ?
            ORDER BY nome
        """, (f"%{nome}%",))
        
        produtos = cursor.fetchall()
        conn.close()
        
        return produtos
    
    def atualizar_produto(self, produto_id: int, **kwargs):
        """Atualiza informações de um produto"""
        campos_permitidos = ['nome', 'descricao', 'categoria', 'localizacao']
        campos = []
        valores = []
        
        for campo, valor in kwargs.items():
            if campo in campos_permitidos:
                campos.append(f"{campo} = ?")
                valores.append(valor)
        
        if not campos:
            return False
        
        valores.append(produto_id)
        
        conn = self.conectar()
        cursor = conn.cursor()
        
        query = f"UPDATE produtos SET {', '.join(campos)} WHERE id = ?"
        cursor.execute(query, valores)
        
        conn.commit()
        linhas_afetadas = cursor.rowcount
        conn.close()
        
        return linhas_afetadas > 0
    
    def registrar_entrada(self, produto_id: int, quantidade: int, 
                         observacao: str = "") -> bool:
        """Registra entrada de produtos no estoque"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute("SELECT quantidade FROM produtos WHERE id = ?", (produto_id,))
        resultado = cursor.fetchone()
        
        if not resultado:
            conn.close()
            return False
        
        quantidade_atual = resultado[0]
        nova_quantidade = quantidade_atual + quantidade
        
        cursor.execute("""
            UPDATE produtos SET quantidade = ? WHERE id = ?
        """, (nova_quantidade, produto_id))
        
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO movimentacoes (produto_id, tipo, quantidade, data_movimentacao, observacao)
            VALUES (?, 'ENTRADA', ?, ?, ?)
        """, (produto_id, quantidade, data_atual, observacao))
        
        conn.commit()
        conn.close()
        
        return True
    
    def registrar_saida(self, produto_id: int, quantidade: int, 
                       observacao: str = "") -> bool:
        """Registra saída de produtos do estoque"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute("SELECT quantidade FROM produtos WHERE id = ?", (produto_id,))
        resultado = cursor.fetchone()
        
        if not resultado:
            conn.close()
            return False
        
        quantidade_atual = resultado[0]
        
        if quantidade_atual < quantidade:
            conn.close()
            return False
        
        nova_quantidade = quantidade_atual - quantidade
        
        cursor.execute("""
            UPDATE produtos SET quantidade = ? WHERE id = ?
        """, (nova_quantidade, produto_id))
        
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO movimentacoes (produto_id, tipo, quantidade, data_movimentacao, observacao)
            VALUES (?, 'SAIDA', ?, ?, ?)
        """, (produto_id, quantidade, data_atual, observacao))
        
        conn.commit()
        conn.close()
        
        return True
    
    def listar_movimentacoes(self, produto_id: Optional[int] = None, data_inicio: Optional[str] = None, data_fim: Optional[str] = None) -> List[Tuple]:
        """Lista movimentações de um produto ou de todos os produtos"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        query = """
            SELECT m.id, p.nome, m.tipo, m.quantidade, m.data_movimentacao, m.observacao
            FROM movimentacoes m
            JOIN produtos p ON m.produto_id = p.id
            WHERE 1=1
        """
        params = []
        
        if produto_id:
            query += " AND m.produto_id = ?"
            params.append(produto_id)
        
        if data_inicio:
            query += " AND DATE(m.data_movimentacao) >= ?"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND DATE(m.data_movimentacao) <= ?"
            params.append(data_fim)
        
        query += " ORDER BY m.data_movimentacao DESC LIMIT 500"
        
        cursor.execute(query, params)
        movimentacoes = cursor.fetchall()
        conn.close()
        
        return movimentacoes
    
    def produtos_estoque_baixo(self, limite: int = 10) -> List[Tuple]:
        """Lista produtos com estoque abaixo do limite especificado"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nome, categoria, quantidade, localizacao
            FROM produtos
            WHERE quantidade <= ?
            ORDER BY quantidade ASC
        """, (limite,))
        
        produtos = cursor.fetchall()
        conn.close()
        
        return produtos
    
    def relatorio_estoque(self) -> dict:
        """Gera um relatório geral do estoque"""
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total_produtos = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(quantidade) FROM produtos")
        total_itens = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT categoria, COUNT(*), SUM(quantidade)
            FROM produtos
            GROUP BY categoria
        """)
        por_categoria = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_produtos': total_produtos,
            'total_itens': total_itens,
            'por_categoria': por_categoria
        }


class InterfaceDeposito:
    def __init__(self, root):
        self.root = root
        self.root.title("🍁 Sistema de Gerenciamento de Depósito")
        self.root.geometry("1000x600")
        self.deposito = GerenciadorDeposito()
        
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        # Notebook (abas)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Criar abas
        self.criar_aba_produtos()
        self.criar_aba_movimentacoes()
        self.criar_aba_relatorios()
        self.criar_aba_manutencao()
        self.criar_aba_sobre()
        
    def criar_aba_produtos(self):
        """Cria a aba de gerenciamento de produtos"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📦 Produtos")
        
        # Frame superior - Formulário
        form_frame = ttk.LabelFrame(frame, text="Cadastro de Produto", padding=10)
        form_frame.pack(fill='x', padx=10, pady=5)
        
        # Campos do formulário
        ttk.Label(form_frame, text="Nome:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.nome_entry = ttk.Entry(form_frame, width=30)
        self.nome_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(form_frame, text="Categoria:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        self.categoria_entry = ttk.Entry(form_frame, width=30)
        self.categoria_entry.grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(form_frame, text="Quantidade:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.quantidade_entry = ttk.Entry(form_frame, width=30)
        self.quantidade_entry.grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(form_frame, text="Localização:").grid(row=1, column=2, sticky='w', padx=5, pady=2)
        self.localizacao_entry = ttk.Entry(form_frame, width=30)
        self.localizacao_entry.grid(row=1, column=3, padx=5, pady=2)
        
        ttk.Label(form_frame, text="Descrição:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.descricao_entry = ttk.Entry(form_frame, width=73)
        self.descricao_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=2)
        
        # Botões
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10)
        
        ttk.Button(btn_frame, text="Adicionar Produto", command=self.adicionar_produto).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Limpar Campos", command=self.limpar_campos_produto).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Atualizar Lista", command=self.atualizar_lista_produtos).pack(side='left', padx=5)
        
        # Frame de busca
        busca_frame = ttk.LabelFrame(frame, text="Localizar Produto", padding=10)
        busca_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(busca_frame, text="Buscar por nome:").pack(side='left', padx=5)
        self.busca_entry = ttk.Entry(busca_frame, width=40)
        self.busca_entry.pack(side='left', padx=5)
        ttk.Button(busca_frame, text="🔍 Buscar", command=self.buscar_produtos).pack(side='left', padx=5)
        ttk.Button(busca_frame, text="Limpar Busca", command=self.limpar_busca).pack(side='left', padx=5)
        
        # Frame inferior - Lista de produtos
        lista_frame = ttk.LabelFrame(frame, text="Lista de Produtos", padding=10)
        lista_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview
        columns = ('ID', 'Nome', 'Categoria', 'Quantidade', 'Localização', 'Descrição')
        self.tree_produtos = ttk.Treeview(lista_frame, columns=columns, show='headings', height=12)
        
        # Definir cabeçalhos
        self.tree_produtos.heading('ID', text='ID')
        self.tree_produtos.heading('Nome', text='Nome')
        self.tree_produtos.heading('Categoria', text='Categoria')
        self.tree_produtos.heading('Quantidade', text='Quantidade')
        self.tree_produtos.heading('Localização', text='Localização')
        self.tree_produtos.heading('Descrição', text='Descrição')
        
        # Definir larguras
        self.tree_produtos.column('ID', width=50)
        self.tree_produtos.column('Nome', width=200)
        self.tree_produtos.column('Categoria', width=120)
        self.tree_produtos.column('Quantidade', width=100)
        self.tree_produtos.column('Localização', width=150)
        self.tree_produtos.column('Descrição', width=200)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(lista_frame, orient='vertical', command=self.tree_produtos.yview)
        self.tree_produtos.configure(yscrollcommand=scrollbar.set)
        
        self.tree_produtos.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Botões de ação
        acoes_frame = ttk.Frame(lista_frame)
        acoes_frame.pack(fill='x', pady=5)
        
        ttk.Button(acoes_frame, text="Entrada", command=self.abrir_entrada).pack(side='left', padx=5)
        ttk.Button(acoes_frame, text="Saída", command=self.abrir_saida).pack(side='left', padx=5)
        
        # Carregar produtos
        self.atualizar_lista_produtos()
        
    def criar_aba_movimentacoes(self):
        """Cria a aba de movimentações"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📋 Movimentações")
        
        # Frame de filtros
        filtro_frame = ttk.LabelFrame(frame, text="Filtrar Movimentações", padding=10)
        filtro_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(filtro_frame, text="Data Início:").pack(side='left', padx=5)
        self.data_inicio_cal = DateEntry(
            filtro_frame, 
            width=12, 
            background='darkblue',
            foreground='white', 
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            locale='pt_BR'
        )
        self.data_inicio_cal.pack(side='left', padx=5)
        
        ttk.Label(filtro_frame, text="Data Fim:").pack(side='left', padx=5)
        self.data_fim_cal = DateEntry(
            filtro_frame, 
            width=12, 
            background='darkblue',
            foreground='white', 
            borderwidth=2,
            date_pattern='yyyy-mm-dd',
            locale='pt_BR'
        )
        self.data_fim_cal.pack(side='left', padx=5)
        
        ttk.Button(filtro_frame, text="Filtrar", command=self.filtrar_movimentacoes).pack(side='left', padx=5)
        ttk.Button(filtro_frame, text="Limpar Filtro", command=self.limpar_filtro_movimentacoes).pack(side='left', padx=5)
        
        # Treeview
        columns = ('ID', 'Produto', 'Tipo', 'Quantidade', 'Data', 'Observação')
        self.tree_movimentacoes = ttk.Treeview(frame, columns=columns, show='headings', height=20)
        
        self.tree_movimentacoes.heading('ID', text='ID')
        self.tree_movimentacoes.heading('Produto', text='Produto')
        self.tree_movimentacoes.heading('Tipo', text='Tipo')
        self.tree_movimentacoes.heading('Quantidade', text='Quantidade')
        self.tree_movimentacoes.heading('Data', text='Data')
        self.tree_movimentacoes.heading('Observação', text='Observação')
        
        self.tree_movimentacoes.column('ID', width=50)
        self.tree_movimentacoes.column('Produto', width=200)
        self.tree_movimentacoes.column('Tipo', width=100)
        self.tree_movimentacoes.column('Quantidade', width=100)
        self.tree_movimentacoes.column('Data', width=150)
        self.tree_movimentacoes.column('Observação', width=250)
        
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.tree_movimentacoes.yview)
        self.tree_movimentacoes.configure(yscrollcommand=scrollbar.set)
        
        self.tree_movimentacoes.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scrollbar.pack(side='right', fill='y', pady=10)
        
        # Botão atualizar
        ttk.Button(frame, text="Atualizar", command=self.atualizar_movimentacoes).pack(pady=5)
        
        self.atualizar_movimentacoes()
        
    def criar_aba_relatorios(self):
        """Cria a aba de relatórios"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📊 Relatórios")
        
        # Frame de botões
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Gerar Relatório Geral", command=self.gerar_relatorio).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Produtos Estoque Baixo", command=self.mostrar_estoque_baixo).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Produtos em Estoque", command=self.mostrar_produtos_em_estoque).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Movimentações 12 Meses", command=self.mostrar_movimentacoes_12_meses).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="💾 Salvar em PDF", command=self.salvar_relatorio_pdf).pack(side='left', padx=5)
        
        # Área de texto para relatório
        self.relatorio_text = scrolledtext.ScrolledText(frame, width=80, height=25, font=('Courier', 10))
        self.relatorio_text.pack(fill='both', expand=True, padx=10, pady=10)
        
    def adicionar_produto(self):
        """Adiciona um novo produto"""
        try:
            nome = self.nome_entry.get().strip()
            categoria = self.categoria_entry.get().strip()
            quantidade = int(self.quantidade_entry.get())
            localizacao = self.localizacao_entry.get().strip()
            descricao = self.descricao_entry.get().strip()
            
            if not nome:
                messagebox.showerror("Erro", "Nome do produto é obrigatório!")
                return
            
            produto_id = self.deposito.adicionar_produto(
                nome=nome,
                quantidade=quantidade,
                descricao=descricao,
                categoria=categoria,
                localizacao=localizacao
            )
            
            messagebox.showinfo("Sucesso", f"Produto cadastrado com ID: {produto_id}")
            self.limpar_campos_produto()
            self.atualizar_lista_produtos()
            
        except ValueError:
            messagebox.showerror("Erro", "Digite um valor válido para quantidade!")
    
    def limpar_campos_produto(self):
        """Limpa os campos do formulário"""
        self.nome_entry.delete(0, tk.END)
        self.categoria_entry.delete(0, tk.END)
        self.quantidade_entry.delete(0, tk.END)
        self.localizacao_entry.delete(0, tk.END)
        self.descricao_entry.delete(0, tk.END)
    
    def atualizar_lista_produtos(self):
        """Atualiza a lista de produtos"""
        for item in self.tree_produtos.get_children():
            self.tree_produtos.delete(item)
        
        produtos = self.deposito.listar_produtos()
        for p in produtos:
            self.tree_produtos.insert('', 'end', values=(
                p[0], p[1], p[3], p[4], p[5], p[2]
            ))
    
    def buscar_produtos(self):
        """Busca produtos por nome"""
        nome = self.busca_entry.get().strip()
        
        if not nome:
            messagebox.showwarning("Atenção", "Digite um nome para buscar!")
            return
        
        for item in self.tree_produtos.get_children():
            self.tree_produtos.delete(item)
        
        produtos = self.deposito.buscar_produto_por_nome(nome)
        
        if not produtos:
            messagebox.showinfo("Busca", "Nenhum produto encontrado!")
            return
        
        for p in produtos:
            self.tree_produtos.insert('', 'end', values=(
                p[0], p[1], p[3], p[4], p[5], p[2]
            ))
        
        messagebox.showinfo("Busca", f"{len(produtos)} produto(s) encontrado(s)!")
    
    def limpar_busca(self):
        """Limpa o campo de busca e recarrega todos os produtos"""
        self.busca_entry.delete(0, tk.END)
        self.atualizar_lista_produtos()
    
    def abrir_entrada(self):
        """Abre janela para registrar entrada"""
        selecionado = self.tree_produtos.selection()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um produto!")
            return
        
        item = self.tree_produtos.item(selecionado[0])
        produto_id = item['values'][0]
        produto_nome = item['values'][1]
        
        self.janela_movimentacao(produto_id, produto_nome, "ENTRADA")
    
    def abrir_saida(self):
        """Abre janela para registrar saída"""
        selecionado = self.tree_produtos.selection()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione um produto!")
            return
        
        item = self.tree_produtos.item(selecionado[0])
        produto_id = item['values'][0]
        produto_nome = item['values'][1]
        quantidade_atual = item['values'][3]
        
        self.janela_movimentacao(produto_id, produto_nome, "SAIDA", quantidade_atual)
    
    def janela_movimentacao(self, produto_id, produto_nome, tipo, qtd_atual=None):
        """Janela para registrar movimentação"""
        janela = tk.Toplevel(self.root)
        janela.title(f"{tipo} - {produto_nome}")
        janela.geometry("400x255")
        
        ttk.Label(janela, text=f"Produto: {produto_nome}", font=('Arial', 12, 'bold')).pack(pady=10)
        
        if qtd_atual:
            ttk.Label(janela, text=f"Quantidade atual: {qtd_atual}").pack()
        
        ttk.Label(janela, text="Quantidade:").pack(pady=5)
        qtd_entry = ttk.Entry(janela, width=20)
        qtd_entry.pack()
        
        ttk.Label(janela, text="Observação:").pack(pady=5)
        obs_entry = ttk.Entry(janela, width=40)
        obs_entry.pack()
        
        def confirmar():
            try:
                quantidade = int(qtd_entry.get())
                observacao = obs_entry.get().strip()
                
                if tipo == "ENTRADA":
                    sucesso = self.deposito.registrar_entrada(produto_id, quantidade, observacao)
                else:
                    sucesso = self.deposito.registrar_saida(produto_id, quantidade, observacao)
                
                if sucesso:
                    messagebox.showinfo("Sucesso", f"{tipo} registrada com sucesso!", parent=janela)
                    janela.destroy()
                    self.atualizar_lista_produtos()
                    self.atualizar_movimentacoes()
                else:
                    messagebox.showerror("Erro", "Quantidade insuficiente em estoque!" if tipo == "SAIDA" else "Erro ao registrar!", parent=janela)
            
            except ValueError:
                messagebox.showerror("Erro", "Digite uma quantidade válida!", parent=janela)
        
        ttk.Button(janela, text="Confirmar", command=confirmar).pack(pady=20)
    
    def atualizar_movimentacoes(self):
        """Atualiza a lista de movimentações - mostra últimos 30 dias"""
        from datetime import date, timedelta
        
        for item in self.tree_movimentacoes.get_children():
            self.tree_movimentacoes.delete(item)
        
        # Calcula data de 30 dias atrás
        data_limite = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Busca movimentações dos últimos 30 dias
        movimentacoes = self.deposito.listar_movimentacoes(
            produto_id=None,
            data_inicio=data_limite,
            data_fim=None
        )
        
        for m in movimentacoes:
            self.tree_movimentacoes.insert('', 'end', values=m)
    
    def filtrar_movimentacoes(self):
        """Filtra movimentações por data"""
        # Pega as datas dos widgets calendário
        data_inicio = self.data_inicio_cal.get_date().strftime('%Y-%m-%d')
        data_fim = self.data_fim_cal.get_date().strftime('%Y-%m-%d')
        
        # Limpa a tabela
        for item in self.tree_movimentacoes.get_children():
            self.tree_movimentacoes.delete(item)
        
        # Busca com filtro
        movimentacoes = self.deposito.listar_movimentacoes(
            produto_id=None,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        if not movimentacoes:
            messagebox.showinfo("Filtro", "Nenhuma movimentação encontrada no período!")
            return
        
        for m in movimentacoes:
            self.tree_movimentacoes.insert('', 'end', values=m)
        
        messagebox.showinfo("Filtro", f"{len(movimentacoes)} movimentação(ões) encontrada(s)!")
    
    def limpar_filtro_movimentacoes(self):
        """Limpa o filtro de datas"""
        from datetime import date
        hoje = date.today()
        self.data_inicio_cal.set_date(hoje)
        self.data_fim_cal.set_date(hoje)
        self.atualizar_movimentacoes()
    
    def gerar_relatorio(self):
        """Gera relatório geral"""
        self.relatorio_text.delete(1.0, tk.END)
        
        relatorio = self.deposito.relatorio_estoque()
        
        texto = "="*60 + "\n"
        texto += "RELATÓRIO GERAL DO ESTOQUE".center(60) + "\n"
        texto += "="*60 + "\n\n"
        texto += f"Total de produtos cadastrados: {relatorio['total_produtos']}\n"
        texto += f"Total de itens em estoque: {relatorio['total_itens']}\n\n"
        texto += "="*60 + "\n"
        texto += "PRODUTOS POR CATEGORIA\n"
        texto += "="*60 + "\n\n"
        
        for cat in relatorio['por_categoria']:
            categoria = cat[0] or "Sem categoria"
            texto += f"{categoria}: {cat[1]} produto(s), {cat[2]} item(ns)\n"
        
        self.relatorio_text.insert(1.0, texto)
    
    def mostrar_estoque_baixo(self):
        """Mostra produtos com estoque baixo"""
        self.relatorio_text.delete(1.0, tk.END)
        
        produtos = self.deposito.produtos_estoque_baixo(10)
        
        texto = "="*80 + "\n"
        texto += "PRODUTOS COM ESTOQUE BAIXO (≤ 10)".center(80) + "\n"
        texto += "="*80 + "\n\n"
        
        if not produtos:
            texto += "Nenhum produto com estoque baixo!\n"
        else:
            texto += f"{'ID':<6} {'Nome':<30} {'Categoria':<15} {'Qtd':<8} {'Localização':<20}\n"
            texto += "-"*80 + "\n"
            for p in produtos:
                texto += f"{p[0]:<6} {p[1]:<30} {p[2] or 'N/A':<15} {p[3]:<8} {p[4] or 'N/A':<20}\n"
            
            texto += "\n" + "="*80 + "\n"
            texto += f"Total: {len(produtos)} produto(s) com estoque baixo\n"
        
        self.relatorio_text.insert(1.0, texto)
    
    def mostrar_produtos_em_estoque(self):
        """Mostra todos os produtos com quantidade maior que 0"""
        self.relatorio_text.delete(1.0, tk.END)
        
        conn = self.deposito.conectar()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nome, categoria, quantidade, localizacao
            FROM produtos
            WHERE quantidade > 0
            ORDER BY nome
        """)
        
        produtos = cursor.fetchall()
        conn.close()
        
        texto = "="*80 + "\n"
        texto += "PRODUTOS EM ESTOQUE (QUANTIDADE > 0)".center(80) + "\n"
        texto += "="*80 + "\n\n"
        
        if not produtos:
            texto += "Nenhum produto em estoque!\n"
        else:
            texto += f"{'ID':<6} {'Nome':<30} {'Categoria':<15} {'Qtd':<8} {'Localização':<20}\n"
            texto += "-"*80 + "\n"
            
            total_itens = 0
            for p in produtos:
                texto += f"{p[0]:<6} {p[1]:<30} {p[2] or 'N/A':<15} {p[3]:<8} {p[4] or 'N/A':<20}\n"
                total_itens += p[3]
            
            texto += "\n" + "="*80 + "\n"
            texto += f"Total de produtos diferentes: {len(produtos)}\n"
            texto += f"Total de itens em estoque: {total_itens}\n"
        
        self.relatorio_text.insert(1.0, texto)
    
    def mostrar_movimentacoes_12_meses(self):
        """Mostra relatório de movimentações dos últimos 12 meses"""
        self.relatorio_text.delete(1.0, tk.END)
        
        conn = self.deposito.conectar()
        cursor = conn.cursor()
        
        # Calcula data de 12 meses atrás
        from datetime import date, timedelta
        data_limite = (date.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # Busca produtos com movimentações nos últimos 12 meses
        cursor.execute("""
            SELECT 
                p.id,
                p.nome,
                p.categoria,
                COALESCE(SUM(CASE WHEN m.tipo = 'ENTRADA' THEN m.quantidade ELSE 0 END), 0) as total_entradas,
                COALESCE(SUM(CASE WHEN m.tipo = 'SAIDA' THEN m.quantidade ELSE 0 END), 0) as total_saidas,
                p.quantidade as estoque_atual
            FROM produtos p
            INNER JOIN movimentacoes m ON p.id = m.produto_id
            WHERE DATE(m.data_movimentacao) >= ?
            GROUP BY p.id, p.nome, p.categoria, p.quantidade
            ORDER BY p.nome
        """, (data_limite,))
        
        produtos = cursor.fetchall()
        conn.close()
        
        texto = "="*95 + "\n"
        texto += "MOVIMENTAÇÕES DOS ÚLTIMOS 12 MESES".center(95) + "\n"
        texto += f"Período: {data_limite} até {date.today().strftime('%Y-%m-%d')}".center(95) + "\n"
        texto += "="*95 + "\n\n"
        
        if not produtos:
            texto += "Nenhuma movimentação nos últimos 12 meses!\n"
        else:
            texto += f"{'ID':<6} {'Produto':<30} {'Categoria':<15} {'Entradas':<12} {'Saídas':<12} {'Saldo':<10}\n"
            texto += "-"*95 + "\n"
            
            total_entradas = 0
            total_saidas = 0
            
            for p in produtos:
                produto_id, nome, categoria, entradas, saidas, estoque = p
                texto += f"{produto_id:<6} {nome:<30} {categoria or 'N/A':<15} {entradas:<12} {saidas:<12} {estoque:<10}\n"
                total_entradas += entradas
                total_saidas += saidas
            
            texto += "\n" + "="*95 + "\n"
            texto += f"Total de produtos com movimentação: {len(produtos)}\n"
            texto += f"Total geral de entradas: {total_entradas}\n"
            texto += f"Total geral de saídas: {total_saidas}\n"
            texto += f"Saldo (Entradas - Saídas): {total_entradas - total_saidas}\n"
        
        self.relatorio_text.insert(1.0, texto)
    
    def salvar_relatorio_pdf(self):
        """Salva o relatório atual em arquivo PDF"""
        conteudo = self.relatorio_text.get(1.0, tk.END).strip()
        
        if not conteudo:
            messagebox.showwarning("Atenção", "Gere um relatório antes de salvar!")
            return
        
        from tkinter import filedialog
        
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
        except ImportError:
            messagebox.showerror(
                "Erro", 
                "Biblioteca ReportLab não instalada!\n\nInstale com: pip install reportlab"
            )
            return
        
        arquivo = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Arquivo PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
            title="Salvar Relatório em PDF"
        )
        
        if arquivo:
            try:
                # Criar canvas PDF
                c = canvas.Canvas(arquivo, pagesize=A4)
                largura, altura = A4
                
                # Configurações
                margem_esquerda = 50
                margem_superior = altura - 50
                espacamento_linha = 14
                y = margem_superior
                
                # Título
                c.setFont("Helvetica-Bold", 16)
                titulo = "Sistema de Gerenciamento de Depósito"
                largura_titulo = c.stringWidth(titulo, "Helvetica-Bold", 16)
                c.drawString((largura - largura_titulo) / 2, y, titulo)
                y -= 30
                
                # Separador
                c.setLineWidth(1)
                c.line(margem_esquerda, y, largura - margem_esquerda, y)
                y -= 20
                
                # Conteúdo do relatório
                c.setFont("Courier", 9)
                linhas = conteudo.split('\n')
                
                for linha in linhas:
                    # Verifica se precisa criar nova página
                    if y < 80:
                        c.showPage()
                        c.setFont("Courier", 9)
                        y = margem_superior
                    
                    # Desenha a linha (limitando o tamanho)
                    if len(linha) > 95:
                        linha = linha[:95]
                    
                    c.drawString(margem_esquerda, y, linha)
                    y -= espacamento_linha
                
                # Rodapé em todas as páginas
                c.setFont("Helvetica", 8)
                rodape = f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
                c.drawString(margem_esquerda, 30, rodape)
                
                # Salvar PDF
                c.save()
                
                messagebox.showinfo("Sucesso", f"Relatório PDF salvo em:\n{arquivo}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar arquivo PDF:\n{str(e)}")
    
    def criar_aba_manutencao(self):
        """Cria a aba de manutenção do sistema"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🔧 Manutenção")
        
        # Frame principal com padding
        main_frame = ttk.Frame(frame, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Título
        titulo = ttk.Label(
            main_frame,
            text="Manutenção do Sistema",
            font=('Arial', 14, 'bold')
        )
        titulo.pack(pady=(0, 20))
        
        # Frame de Backup
        backup_frame = ttk.LabelFrame(main_frame, text="Backup do Banco de Dados", padding=15)
        backup_frame.pack(fill='x', pady=10)
        
        desc_backup = ttk.Label(
            backup_frame,
            text="Crie uma cópia de segurança do banco de dados.\nRecomenda-se fazer backups regularmente.",
            justify='left'
        )
        desc_backup.pack(anchor='w', pady=5)
        
        ttk.Button(
            backup_frame,
            text="💾 Fazer Backup",
            command=self.fazer_backup
        ).pack(pady=10)
        
        # Frame de Restauração
        restaurar_frame = ttk.LabelFrame(main_frame, text="Restaurar Banco de Dados", padding=15)
        restaurar_frame.pack(fill='x', pady=10)
        
        desc_restaurar = ttk.Label(
            restaurar_frame,
            text="Restaure o banco de dados a partir de um backup anterior.\n⚠️ ATENÇÃO: Esta ação substituirá todos os dados atuais!",
            justify='left',
            foreground='red'
        )
        desc_restaurar.pack(anchor='w', pady=5)
        
        ttk.Button(
            restaurar_frame,
            text="📂 Restaurar Backup",
            command=self.restaurar_backup
        ).pack(pady=10)
    
    def fazer_backup(self):
        """Realiza backup do banco de dados"""
        from tkinter import filedialog
        import shutil
        
        arquivo = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("Banco de Dados SQLite", "*.db"), ("Todos os arquivos", "*.*")],
            title="Salvar Backup",
            initialfile=f"backup_deposito_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        
        if arquivo:
            try:
                # Copia o arquivo do banco de dados
                shutil.copy2(self.deposito.db_name, arquivo)
                messagebox.showinfo(
                    "Sucesso",
                    f"Backup realizado com sucesso!\n\nArquivo salvo em:\n{arquivo}"
                )
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao realizar backup:\n{str(e)}")
    
    def restaurar_backup(self):
        """Restaura o banco de dados a partir de um backup"""
        from tkinter import filedialog
        import shutil
        
        # Confirmação
        resposta = messagebox.askyesno(
            "Confirmação",
            "⚠️ ATENÇÃO!\n\nEsta ação substituirá TODOS os dados atuais pelo backup selecionado.\n\n"
            "Deseja continuar?",
            icon='warning'
        )
        
        if not resposta:
            return
        
        arquivo = filedialog.askopenfilename(
            filetypes=[("Banco de Dados SQLite", "*.db"), ("Todos os arquivos", "*.*")],
            title="Selecionar Arquivo de Backup"
        )
        
        if arquivo:
            try:
                # Fecha conexões existentes
                self.deposito.conectar().close()
                
                # Restaura o backup
                shutil.copy2(arquivo, self.deposito.db_name)
                
                messagebox.showinfo(
                    "Sucesso",
                    "Backup restaurado com sucesso!\n\nO sistema será atualizado."
                )
                
                # Atualiza as listas
                self.atualizar_lista_produtos()
                self.atualizar_movimentacoes()
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao restaurar backup:\n{str(e)}")
    
    def criar_aba_sobre(self):
        """Cria a aba Sobre o Sistema"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="ℹ️ Sobre")
        
        # Frame principal com padding
        main_frame = ttk.Frame(frame, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Título
        titulo = ttk.Label(
            main_frame,
            text="Sistema de Gerenciamento de Depósito",
            font=('Arial', 16, 'bold')
        )
        titulo.pack(pady=(0, 10))
        
        # Versão
        versao = ttk.Label(
            main_frame,
            text="Versão 1.1.0",
            font=('Arial', 10)
        )
        versao.pack(pady=(0, 20))
        
        # Frame de descrição
        desc_frame = ttk.LabelFrame(main_frame, text="Sobre o Sistema", padding=15)
        desc_frame.pack(fill='both', expand=True, pady=10)
        
        descricao_texto = """Sistema completo para controle e gerenciamento de estoque de depósitos.

📦 PRINCIPAIS FUNCIONALIDADES:

• Cadastro de produtos com informações detalhadas
• Controle de entradas e saídas de mercadorias
• Busca e localização rápida de produtos
• Histórico completo de movimentações
• Filtros de movimentações por período
• Relatórios gerenciais em PDF
• Backup e restauração do banco de dados

🎯 FINALIDADES DO SISTEMA:

Este sistema foi desenvolvido para facilitar o controle de estoque em depósitos,
permitindo o acompanhamento detalhado de produtos, movimentações e disponibilidade.
Com ele você pode organizar seu estoque de forma eficiente, gerar relatórios para
análise e tomar decisões baseadas em dados concretos.

Ideal para pequenas e médias empresas que necessitam de um controle preciso
de seus produtos em estoque.

💻 Desenvolvido por Felipe da Silva Braz e licenciado em GPLv3 (GNU General Public License versão 3).
"""
        
        texto_desc = scrolledtext.ScrolledText(
            desc_frame,
            wrap='word',
            font=('Arial', 10),
            height=20,
            relief='flat',
            bg='#f0f0f0'
        )
        texto_desc.pack(fill='both', expand=True)
        texto_desc.insert(1.0, descricao_texto)
        texto_desc.config(state='disabled')
 
if __name__ == "__main__":
    root = tk.Tk()
    app = InterfaceDeposito(root)
    root.mainloop()