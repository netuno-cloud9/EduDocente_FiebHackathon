from odoo import models, fields

class pesquisas(models.Model):
    _name = 'blue.edu.pesquisas'
    _description = 'Edu - Pesquisas'

    edu_id = fields.Many2one('blue.edu') 
    cod_docente = fields.Char(string='Código Docente')
    pesquisas = fields.Integer(string='Quantidade de Pesquisas Aplicadas')
    respondidas = fields.Integer(string='Quantidade de Pesquisas Respondidas')
    percentual_respondidas = fields.Float(string='% de Pesquisas Respondidas')
    unidade = fields.Char(string='Nome da Unidade')
    modalidade = fields.Char(string='Nome da Modalidade do Curso')
    curso = fields.Char(string='Nome do Curso')
    disciplina = fields.Char(string='Nome da Disciplina')
    id_turma_disc = fields.Integer(string='Identificador Único da Turma/Disciplina')
    cod_turma = fields.Char(string='Código da Turma')
    tipo_turma = fields.Char(string='Tipo da Turma')
