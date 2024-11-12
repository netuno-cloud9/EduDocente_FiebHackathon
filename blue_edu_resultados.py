from odoo import models, fields

class resultados(models.Model):
    _name = 'blue.edu.resultados'
    _description = 'Edu - Resultados'

    edu_id = fields.Many2one('blue.edu')
    cod_docente = fields.Char(string='Código Docente')
    id_turma_disc = fields.Integer(string='Identificador Único da Turma/Disciplina')
    dt_inicial = fields.Datetime(string='Data Inicial')
    dt_final = fields.Datetime(string='Data Final')
    unidade = fields.Char(string='Nome da Unidade', size=100)
    modalidade = fields.Char(string='Nome da Modalidade do Curso', size=60)
    curso = fields.Char(string='Nome do Curso', size=500)
    disciplina = fields.Char(string='Nome da Disciplina', size=150)
    cod_turma = fields.Char(string='Código da Turma', size=20)
    aula = fields.Integer(string='Número da Aula')
    data_aula = fields.Datetime(string='Data da Aula')
    periodo_letivo = fields.Char(string='Período Letivo')
