from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'postgresql://postgres:1234@127.0.0.1:5432/scsdata'
)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Usuario(db.Model, UserMixin): 
    __tablename__ = 'usuario'
    
    id_usuario = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False) 
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ativo = db.Column(db.Boolean, default=True)

    produtos = db.relationship('Produto', backref='autor', lazy=True)
    clientes = db.relationship('Cliente', backref='vendedor', lazy=True)

    @property
    def id(self):
        return self.id_usuario
    
    def get_id(self):
        return str(self.id_usuario)


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id)) 

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
    
    id_produto = db.Column(db.Integer, primary_key=True) 
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    codigo_mk = db.Column(db.String(50))
    nome = db.Column(db.String(100), nullable=False)
    preco_venda_sugerido = db.Column(db.Float)
    custo_medio_atual = db.Column(db.Float)
    estoque_minimo = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)
    url_foto = db.Column(db.String(255), default='default_produto.png')
    tipo = db.Column(db.String(50), default='Geral')

class Venda(db.Model):
    __tablename__ = 'venda'
    id_venda = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    id_produto = db.Column(db.Integer, db.ForeignKey('produto.id_produto'), nullable=False) 
    nome_cliente_venda = db.Column(db.String(100), nullable=False)
    quantidade_vendida = db.Column(db.Integer, default=1)
    data_venda = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    valor_venda = db.Column(db.Float, default=0.0)
    desconto_total = db.Column(db.Float, default=0.0)
    valor_final = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20))
    

    produto = db.relationship('Produto', backref='vendas')

class Compra(db.Model):
    __tablename__ = 'compra'
    id_compra = db.Column(db.Integer, primary_key=True)
    data_compra = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    total_gasto = db.Column(db.Float)
    desconto = db.Column(db.Float)
    frete = db.Column(db.Integer)
    id_usuario = db.Column(db.Integer)    

    
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_digitado = request.form.get('email')
        senha_digitada = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(email=email_digitado).first()
        
        if usuario and check_password_hash(usuario.senha, senha_digitada):
            login_user(usuario) 
            return redirect(url_for('estoque')) 
        else:
            return render_template('login.html', erro="E-mail ou senha inválidos.")

    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha_plana = request.form.get('senha')
        
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            return "Este e-mail já está cadastrado. Tente fazer login."

        hash_da_senha = generate_password_hash(senha_plana)

        novo_usuario = Usuario(
            nome=nome,
            email=email,
            senha=hash_da_senha, 
            ativo=True
        )

        try:
            db.session.add(novo_usuario)
            db.session.commit()
            print(f"Usuário {nome} cadastrado com sucesso!")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            return f"Erro ao cadastrar: {e}"

    return render_template('cadastro.html')


@app.route('/estoque')
@login_required
def estoque():
    # Busca todos os produtos do banco de dados
    lista_produtos = Produto.query.filter_by(id_usuario=current_user.id).all()
    return render_template('estoque.html', produtos=lista_produtos)

@app.route('/logout')
@login_required 
def logout():
    logout_user() 
    print("Sessão encerrada com sucesso.")
    return redirect(url_for('login'))


@app.route('/cadastrar_produto', methods=['GET', 'POST'])
def cadastrar_produto():
    if request.method == 'POST':
        nome = request.form.get('nome')
        codigo = request.form.get('codigo_mk')
        preco_venda = request.form.get('preco_venda')
        custo = request.form.get('custo')
        quantidade = request.form.get('quantidade')
        
        novo_produto = Produto(
            nome=nome,
            codigo_mk=codigo,
            preco_venda_sugerido=float(preco_venda),
            custo_medio_atual=float(custo),
            estoque_minimo=int(quantidade),
            id_usuario=current_user.id_usuario 
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
        
    return redirect(url_for('estoque'))

@app.route('/formulario_editar/<int:id>')
def formulario_editar(id):
    produto = Produto.query.get_or_404(id)
    return render_template('formulario_editar.html', produto=produto)

@app.route('/atualizar/<int:id>', methods=['POST'])
def atualizar_produto(id):
    produto = Produto.query.get_or_404(id)
    
    produto.nome = request.form.get('nome')
    produto.codigo_mk = request.form.get('codigo_mk')
    produto.preco_venda_sugerido = float(request.form.get('preco_venda'))
    produto.estoque_minimo = int(request.form.get('quantidade'))
    
    try:
        db.session.commit()
        print(f"Produto {id} atualizado!")
        return redirect(url_for('estoque'))
    except Exception as e:
        db.session.rollback()
        return f"Erro ao atualizar: {e}"
    
@app.route('/compras')
@login_required
def compras():
    lista_produtos = Produto.query.filter(Produto.id_usuario == None).all()
    return render_template('compras.html', produtos=lista_produtos)
    
@app.route('/cadastrar_compra', methods=['POST'])
def cadastrar_compra():
    data_compra = request.form.get('data_compra')
    total_gasto_str = request.form.get('total_gasto')
    desconto_str = request.form.get('desconto')
    frete_str = request.form.get('frete')

    ids_produtos = request.form.getlist('id_produto[]')
    quantidades = request.form.getlist('quantidade[]')

    try:
        valor_total = float(total_gasto_str) if total_gasto_str else 0.0
        valor_desconto = float(desconto_str) if desconto_str else 0.0
        valor_frete = int(frete_str) if frete_str else 0 
        
        nova_compra = Compra(
            total_gasto=valor_total,
            desconto=valor_desconto,
            frete=valor_frete,
            id_usuario=current_user.id_usuario
        )
        db.session.add(nova_compra)
        
        for id_prod, qtd in zip(ids_produtos, quantidades):
            if id_prod and qtd:
                
                produto_catalogo = Produto.query.get(int(id_prod))
                
                if produto_catalogo:
                    # 2. Verifica se a consultora logada JÁ TEM esse produto no estoque pessoal dela
                    produto_usuario = Produto.query.filter_by(
                        codigo_mk=produto_catalogo.codigo_mk,
                        id_usuario=current_user.id_usuario
                    ).first()
                    
                    if produto_usuario:
                        # Se ela já tem no estoque, apenas soma a quantidade que chegou
                        produto_usuario.estoque_minimo += int(qtd)
                    else:
                        # Se ela NÃO tem, o sistema cria o registro no estoque DELA na hora!
                        novo_estoque = Produto(
                            id_usuario=current_user.id_usuario,
                            codigo_mk=produto_catalogo.codigo_mk,
                            nome=produto_catalogo.nome,
                            preco_venda_sugerido=produto_catalogo.preco_venda_sugerido,
                            custo_medio_atual=produto_catalogo.custo_medio_atual,
                            estoque_minimo=int(qtd),
                            url_foto=produto_catalogo.url_foto,
                            tipo=produto_catalogo.tipo
                        )
                        db.session.add(novo_estoque)

        # 6. Salva todas as operações no banco
        db.session.commit()
        return redirect(url_for('estoque'))

    except Exception as e:
        db.session.rollback() # Se der qualquer erro, ele desfaz tanto o estoque quanto o gasto
        print(f"Erro ao registrar o lote de compras: {e}")
        return f"Erro ao processar a compra: {e}"
    
@app.route('/historico_compras')
@login_required
def historico_compras():
    # Busca todas as compras do usuário atual, ordenadas pela data (mais nova primeiro)
    compras_realizadas = Compra.query.filter_by(id_usuario=current_user.id_usuario)\
                                     .order_by(Compra.data_compra.desc()).all()
    
    return render_template('historico_compras.html', compras=compras_realizadas)    
    
@app.route('/vendas')
def vendas():
    todas_vendas = Venda.query.order_by(Venda.data_venda.desc()).filter_by(id_usuario=current_user.id).all()
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
            qtd_vendida = 0
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
            id_usuario=current_user.id_usuario
        )
        
        # 2. Baixar o Estoque do Produto
        produto = Produto.query.get(id_prod)
        if produto:
            produto.estoque_minimo -= qtd_vendida
        
        db.session.add(venda_nova)
        db.session.commit()
        return redirect(url_for('vendas'))
        
    produtos = Produto.query.filter_by(id_usuario=current_user.id).all()
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

@app.route('/dashboard')
@login_required
def dashboard():
    soma_vendas = db.session.query(func.sum(Venda.valor_final))\
                    .filter(Venda.id_usuario == current_user.id_usuario).scalar()
                    
    total_vendas = soma_vendas if soma_vendas else 0.0

    soma_compras = db.session.query(func.sum(Compra.total_gasto))\
                    .filter(Compra.id_usuario == current_user.id_usuario).scalar()
    total_compras = soma_compras if soma_compras else 0.0
    
    lucro = total_vendas - total_compras
    
    return render_template('dashboard.html', 
                           total_vendas=total_vendas,
                           total_compras=total_compras,
                           lucro=lucro)

if __name__ == '__main__':
    with app.app_context():
        print("Sincronizando modelos com o banco scsdata...")
        db.create_all()
        print("Todas as tabelas do modelo foram criadas com sucesso!")
    
    app.run(debug=True)

