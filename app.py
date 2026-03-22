from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Configuração de conexão (ajustada para seu banco e senha)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1234@127.0.0.1:5432/scsdata'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS BASEADOS NO SEU DIAGRAMA ---

class Usuario(db.Model):
    __tablename__ = 'usuario'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc))
    ativo = db.Column(db.Boolean, default=True)

    # Relacionamentos (Um usuário possui vários produtos, clientes, etc)
    produtos = db.relationship('Produto', backref='autor', lazy=True)
    clientes = db.relationship('Cliente', backref='vendedor', lazy=True)

class Cliente(db.Model):
    __tablename__ = 'cliente'
    id_cliente = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    anotacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=lambda:datetime.now(timezone.utc))

class Produto(db.Model):
    __tablename__ = 'produto'
    # Garante que o nome seja EXATAMENTE id_produto
    id_produto = db.Column(db.Integer, primary_key=True) 
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    codigo_mk = db.Column(db.String(50))
    nome = db.Column(db.String(100), nullable=False)
    preco_venda_sugerido = db.Column(db.Float)
    custo_medio_atual = db.Column(db.Float)
    estoque_minimo = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)


class Venda(db.Model):
    __tablename__ = 'venda'
    id_venda = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    id_produto = db.Column(db.Integer, db.ForeignKey('produto.id_produto'), nullable=False) # Ligação com o produto
    nome_cliente_venda = db.Column(db.String(100), nullable=False)
    quantidade_vendida = db.Column(db.Integer, default=1) # Quantidade da venda
    data_venda = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    valor_venda = db.Column(db.Float, default=0.0)
    desconto_total = db.Column(db.Float, default=0.0)
    valor_final = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20))
    
    # Relacionamento para podermos exibir o nome do produto na lista de vendas
    produto = db.relationship('Produto', backref='vendas')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_digitado = request.form.get('email')
        senha_digitada = request.form.get('senha')
        
        # Busca o usuário no banco pelo e-mail
        usuario = Usuario.query.filter_by(email=email_digitado).first()
        
        if usuario and usuario.senha_hash == senha_digitada:
            # Login com sucesso! Por enquanto, vamos mandar para o Estoque (tela inicial)
            print(f"Login realizado: {usuario.nome}")
            return redirect(url_for('estoque'))
        else:
            print("Erro: E-mail ou senha incorretos.")
            return "E-mail ou senha incorretos. <a href='/login'>Tentar novamente</a>"
            
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        # Criando o novo usuário no banco
        novo_usuario = Usuario(nome=nome, email=email, senha_hash=senha) # No futuro usaremos criptografia aqui
        
        try:
            db.session.add(novo_usuario)
            db.session.commit()
            print(f"Usuário {nome} cadastrado com sucesso!")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao cadastrar: {e}")
            return "Erro ao cadastrar. O e-mail já pode estar em uso."
            
    return render_template('cadastro.html')

@app.route('/estoque')
def estoque():
    # Por enquanto estamos passando uma lista fake só para ver o visual
    return render_template('estoque.html')


@app.route('/cadastrar_produto', methods=['GET', 'POST'])
def cadastrar_produto():
    if request.method == 'POST':
        # Pegando os dados do formulário
        nome = request.form.get('nome')
        codigo = request.form.get('codigo_mk')
        preco_venda = request.form.get('preco_venda')
        custo = request.form.get('custo')
        quantidade = request.form.get('quantidade')

        # Criando o objeto do produto (id_usuario=1 assume que você já criou um usuário)
        novo_produto = Produto(
            nome=nome,
            codigo_mk=codigo,
            preco_venda_sugerido=float(preco_venda),
            custo_medio_atual=float(custo),
            estoque_minimo=int(quantidade), # Usando estoque_minimo para fins ilustrativos agora
            id_usuario=1 
        )

        try:
            db.session.add(novo_produto)
            db.session.commit()
            print(f"Produto {nome} cadastrado!")
            return redirect(url_for('estoque'))
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao cadastrar produto: {e}")
            return "Erro ao salvar o produto no banco."

    return render_template('cadastrar_produto.html')

@app.route('/produtos')
def produtos_disponiveis():
    # Busca todos os produtos do banco de dados
    lista_produtos = Produto.query.all()
    return render_template('produtos.html', produtos=lista_produtos)

# Rota para ver a lista de exclusão
@app.route('/excluir_produto')
def excluir_produto_view():
    lista_produtos = Produto.query.all()
    return render_template('excluir_produto.html', produtos=lista_produtos)

# Rota que realmente deleta o item
@app.route('/deletar/<int:id>', methods=['POST'])
def deletar_produto(id):
    produto_para_deletar = Produto.query.get_or_404(id)
    
    try:
        db.session.delete(produto_para_deletar)
        db.session.commit()
        print(f"Produto ID {id} excluído com sucesso.")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao excluir: {e}")
        
    return redirect(url_for('excluir_produto_view'))

# 1. Rota para listar os produtos que podem ser editados
@app.route('/editar_produto')
def editar_produto_view():
    lista_produtos = Produto.query.all()
    return render_template('editar_produto.html', produtos=lista_produtos)

# 2. Rota para abrir o formulário com os dados do produto escolhido
@app.route('/formulario_editar/<int:id>')
def formulario_editar(id):
    produto = Produto.query.get_or_404(id)
    return render_template('formulario_editar.html', produto=produto)

# 3. Rota para processar a atualização no banco
@app.route('/atualizar/<int:id>', methods=['POST'])
def atualizar_produto(id):
    produto = Produto.query.get_or_404(id)
    
    # Atualizando os campos com o que veio do formulário
    produto.nome = request.form.get('nome')
    produto.codigo_mk = request.form.get('codigo_mk')
    produto.preco_venda_sugerido = float(request.form.get('preco_venda'))
    produto.estoque_minimo = int(request.form.get('quantidade'))
    
    try:
        db.session.commit()
        print(f"Produto {id} atualizado!")
        return redirect(url_for('editar_produto_view'))
    except Exception as e:
        db.session.rollback()
        return f"Erro ao atualizar: {e}"
    
@app.route('/vendas')
def vendas():
    todas_vendas = Venda.query.order_by(Venda.data_venda.desc()).all()
    return render_template('vendas.html', vendas=todas_vendas)

@app.route('/nova_venda', methods=['GET', 'POST'])
def nova_venda():
    if request.method == 'POST':
        print(request.form)
        print("Botão clicado! Recebendo dados...")
        id_prod = request.form.get('id_produto')
        print(f"ID do Produto selecionado: {id_prod}")
        qtd_str = request.form.get('quantidade')
        if qtd_str is None or qtd_str == '':
            qtd_vendida = 0  # Valor padrão se vier vazio
        else:
            qtd_vendida = int(qtd_str)
        nome = request.form.get('nome_cliente')
        valor_venda_bruto = request.form.get('valor_venda')
        valor_venda = float(valor_venda_bruto) if valor_venda_bruto else 0.0

        desconto_bruto = request.form.get('desconto')
        desconto = float(desconto_bruto) if desconto_bruto else 0.0
        status = request.form.get('status')
        
        valor_final = valor_venda - desconto
        
        # 1. Registrar a Venda
        venda_nova = Venda(
            id_produto=id_prod,
            quantidade_vendida=qtd_vendida,
            nome_cliente_venda=nome,
            valor_venda=valor_venda,
            desconto_total=desconto,
            valor_final=valor_final,
            status=status,
            id_usuario=1
        )
        
        # 2. Baixar o Estoque do Produto
        produto = Produto.query.get(id_prod)
        if produto:
            produto.estoque_minimo -= qtd_vendida # Subtrai do estoque atual
        
        db.session.add(venda_nova)
        db.session.commit()
        return redirect(url_for('vendas'))
        
    # GET: Carrega a lista de produtos para o <select> do formulário
    produtos = Produto.query.all()
    return render_template('nova_venda.html', produtos=produtos)

@app.route('/pagar_venda/<int:id>', methods=['POST'])
def pagar_venda(id):
    venda = Venda.query.get_or_404(id)
    venda.status = 'Pago'
    
    try:
        db.session.commit()
        print(f"Venda {id} marcada como Paga!")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao atualizar status: {e}")
        
    return redirect(url_for('vendas'))

# --- COMANDO PARA CRIAR AS TABELAS ---
if __name__ == '__main__':
    with app.app_context():
        print("Sincronizando modelos com o banco scsdata...")
        # Dica: db.drop_all() apagaria as tabelas antigas para criar as novas
        # Use com cuidado se já tiver dados!
        db.create_all()
        print("Todas as tabelas do modelo foram criadas com sucesso!")
    
    app.run(debug=True)

