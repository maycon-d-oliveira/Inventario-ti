"""
Arquivo: forms.py
Propósito:
    Definir formulários para autenticação e manutenção usando Flask-WTF.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, DecimalField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange, Optional


class LoginForm(FlaskForm):
    """Formulário de login."""
    username = StringField('Usuário', validators=[
        DataRequired(),
        Length(min=3, max=25)
    ])
    password = PasswordField('Senha', validators=[
        DataRequired()
    ])
    remember = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')


class RegistrationForm(FlaskForm):
    """Formulário de registro."""
    username = StringField('Usuário', validators=[
        DataRequired(),
        Length(min=3, max=25)
    ])
    email = StringField('E-mail', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Senha', validators=[
        DataRequired(),
        Length(min=6)
    ])
    confirm_password = PasswordField('Confirmar Senha', validators=[
        DataRequired(),
        EqualTo('password', message='As senhas devem ser iguais.')
    ])
    is_admin = BooleanField('Registrar como Administrador')
    submit = SubmitField('Registrar')

    # Note: Custom validation for unique username/email will be handled in the route


class ManutencaoForm(FlaskForm):
    """Formulário de manutenção."""
    aparelho_id = StringField('Aparelho ID', validators=[
        DataRequired(),
        Length(min=1, max=50)
    ])
    status_manutencao = SelectField('Status', choices=[
        ('aguardando_peca', 'Aguardando Peça'),
        ('em_reparo', 'Em Reparo'),
        ('aguardando_aprovacao', 'Aguardando Aprovação'),
        ('pronto', 'Pronto'),
        ('entregue', 'Entregue'),
        ('cancelado', 'Cancelado')
    ], validators=[
        DataRequired()
    ])
    previsao_saida = DateField('Previsão de Saída', validators=[
        Optional()
    ])
    descricao_problema = TextAreaField('Descrição do Problema', validators=[
        DataRequired(),
        Length(min=1, max=2000)
    ])
    solucao = TextAreaField('Solução Aplicada', validators=[
        Optional(),
        Length(max=2000)
    ])
    tecnico_responsavel = StringField('Técnico Responsável', validators=[
        Optional(),
        Length(max=100)
    ])
    valor_custo = DecimalField('Valor do Custo', validators=[
        Optional(),
        NumberRange(min=0)
    ])
    fornecedor = StringField('Fornecedor', validators=[
        Optional(),
        Length(max=100)
    ])
    observacoes = TextAreaField('Observações', validators=[
        Optional(),
        Length(max=2000)
    ])
    submit = SubmitField('Salvar')