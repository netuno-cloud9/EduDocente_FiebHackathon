from odoo import models, fields, api
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class BlueEdu(models.Model):
    _name = 'blue.edu'
    _description = 'Edu Docente'

    ano = fields.Char(string='Ano')
    modalidade = fields.One2many('blue.edu.apuracao', 'edu_id', string='Apuração de resultados')
    curso = fields.Char(string='Curso')
    disciplina = fields.Char(string='Disciplina')
    docente = fields.Char(string='Docente')
    cod_turma = fields.Char(string='Código da Turma')
    unidade = fields.Char(string='Unidade')
    pesquisas = fields.One2many('blue.edu.pesquisas', 'edu_id', string='Pesquisas')
    respondidas = fields.Integer(string='Respondidas')
    percentual_respondidas = fields.Float(string='% Respondidas')
    id_turma = fields.One2many('blue.edu.resultados', 'edu_id', string='Pendencia de apuração de resultado')
    dt_fim_disc = fields.Date(string='Data Fim Disciplina')
    dt_fim = fields.Date(string='Data Fim')
    tipo_turma = fields.Char(string='Tipo de Turma')
    cod_docente = fields.One2many('blue.edu.pendencias', 'edu_id', string='Medias')
    cod_prof = fields.Char(string='Código Professor')
    user_id = fields.Many2one('res.users', string='Usuário')
    total_apuracao = fields.Integer(string='Total Apuração', compute='_compute_total_apuracao', store=True)
    total_pesquisas = fields.Integer(string='Total Pesquisas', compute='_compute_total_pesquisas', store=True)
    total_resultados = fields.Integer(string='Total Resultados', compute='_compute_total_resultados', store=True)
    total_pendencias = fields.Integer(string='Total Pendências', compute='_compute_total_pendencias', store=True)

    @api.model
    def create(self, vals):
        record = super(BlueEdu, self).create(vals)
        _logger.info(f"Registro criado com sucesso: {record}")
        return record

    def write(self, vals):
        result = super(BlueEdu, self).write(vals)
        _logger.info(f"Registro atualizado com sucesso: {self}")
        return result

    def _make_api_request(self, cod_sentenca, cod_prof):
        url = "https://senaiweb.fieb.org.br/FrameHTML/rm/api/TOTVSCustomizacao/ConsultasSQL/ExecutaConsultaSQL"
        params = {
            'codColigada': '1',
            'codSentenca': cod_sentenca,
            'codSistema': 'S',
            'parameters': f'codColigada=1;codProf={cod_prof}'
        }
        headers = {'Authorization': 'Basic ZmFnbmVyLnNhbnRhbmE6TTNzdHJl'}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'Row' in data:
                return data
            else:
                self.env.cr.rollback()
                raise ValueError("Resposta inesperada da API: 'Row' não encontrado.")
                
        except requests.exceptions.RequestException as req_err:
            self.env.cr.rollback()
            raise ValueError(f"Erro ao fazer a requisição à API: {req_err}")

    def _raise_error(self, message):
        self.env.cr.rollback()
        raise ValueError(message)

    def consultar_docentes(self, batch_size=20):
        users_with_cod_prof = self.env['res.users'].search([('cod_prof', '!=', False)])
        
        if not users_with_cod_prof:
            raise ValueError("Nenhum usuário com o campo 'cod_prof' preenchido foi encontrado.")

        total_users = len(users_with_cod_prof)
        
        for start in range(0, total_users, batch_size):
            batch_users = users_with_cod_prof[start:start + batch_size]
            
            for user in batch_users:
                try:
                    resultado = self._make_api_request('EDUAPP04', user.cod_prof)
                    
                    if 'Row' in resultado and resultado['Row']:
                        resultado_data_list = resultado['Row']
                        for docente_data in resultado_data_list:
                            self._create_or_update_docente(docente_data, user)
                    else:
                        _logger.info(f"Nenhum docente encontrado ou 'Row' não presente para o usuário {user.name} com cod_prof {user.cod_prof}")
                        
                except ValueError as e:
                    _logger.error(f"Erro ao consultar docentes para o usuário {user.name}: {e}")

            self.env.cr.commit()
            _logger.info(f"Lote de {len(batch_users)} usuários processado com sucesso. Total processado: {start + len(batch_users)}/{total_users}")

        _logger.info("Processamento de todos os docentes concluído com sucesso.")

        # Adiciona a mensagem de sucesso
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sucesso',
                'message': 'Consulta de docentes concluída com sucesso.',
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_or_update_docente(self, docente_data, user):
        record = self.search([('cod_prof', '=', docente_data['CODPROF'])], limit=1)
        values = {
            'cod_prof': docente_data['CODPROF'],
            'docente': docente_data['DOCENTE'],
            'user_id': user.id
        }

        if record:
            _logger.info(f"Atualizando registro para o docente {docente_data['DOCENTE']} com cod_prof {docente_data['CODPROF']}")
            record.write(values)
        else:
            _logger.info(f"Criando registro para o docente {docente_data['DOCENTE']} com cod_prof {docente_data['CODPROF']}")
            self.create(values)

    def consultar_pesquisas(self, batch_size=20):
        docentes = self.search([('cod_prof', '!=', False)])
        
        if not docentes:
            raise ValueError("Nenhum docente com o campo 'cod_prof' preenchido foi encontrado.")

        total_docentes = len(docentes)
        
        for start in range(0, total_docentes, batch_size):
            batch_docentes = docentes[start:start + batch_size]
            
            for docente in batch_docentes:
                try:
                    resultado = self._make_api_request('EDUAPP01', docente.cod_prof)
                    
                    if 'Row' in resultado and resultado['Row']:
                        resultado_data_list = resultado['Row']
                        for pesquisa_data in resultado_data_list:
                            self._create_or_update_pesquisa(pesquisa_data, docente)
                    else:
                        _logger.info(f"Nenhuma pesquisa encontrada ou 'Row' não presente para o docente {docente.docente} com cod_prof {docente.cod_prof}")
                        
                except ValueError as e:
                    _logger.error(f"Erro ao consultar pesquisas para o docente {docente.docente}: {e}")

            self.env.cr.commit()
            _logger.info(f"Lote de {len(batch_docentes)} docentes processado com sucesso. Total processado: {start + len(batch_docentes)}/{total_docentes}")

        _logger.info("Processamento de todas as pesquisas concluído com sucesso.")

        # Adiciona a mensagem de sucesso
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sucesso',
                'message': 'Consulta de pesquisas concluída com sucesso.',
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_or_update_pesquisa(self, pesquisa_data, docente):
        pesquisas_model = self.env['blue.edu.pesquisas']
        
        pesquisa_record = pesquisas_model.search([
            ('id_turma_disc', '=', pesquisa_data['IDTURMADISC']),
            ('cod_docente', '=', pesquisa_data['CODPROF']),
            ('edu_id', '=', docente.id)
        ], limit=1)

        values = {
            'edu_id': docente.id,
            'cod_docente': pesquisa_data['CODPROF'],
            'pesquisas': pesquisa_data['PESQUISAS'],
            'respondidas': pesquisa_data['RESPONDIDAS'],
            'percentual_respondidas': pesquisa_data['%_RESPONDIDAS'],
            'unidade': pesquisa_data['UNIDADE'],
            'modalidade': pesquisa_data['MODALIDADE'],
            'curso': pesquisa_data['CURSO'],
            'disciplina': pesquisa_data['DISCIPLINA'],
            'id_turma_disc': pesquisa_data['IDTURMADISC'],
            'cod_turma': pesquisa_data['CODTURMA'],
            'tipo_turma': pesquisa_data['TIPO_TURMA'],
        }

        if pesquisa_record:
            _logger.info(f"Atualizando pesquisa com ID {pesquisa_data['IDTURMADISC']} para o docente {docente.docente}")
            pesquisa_record.write(values)
        else:
            _logger.info(f"Criando pesquisa com ID {pesquisa_data['IDTURMADISC']} para o docente {docente.docente}")
            pesquisas_model.create(values)

    def _update_total_pesquisas(self, docente):
        total_pesquisas = self.env['blue.edu.pesquisas'].search_count([('edu_id', '=', docente.id)])
        docente.total_pesquisas = total_pesquisas
        _logger.info(f"Total de pesquisas atualizado para o docente {docente.docente}: {total_pesquisas}")

    def _convert_date(self, date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            _logger.error(f"Erro ao converter a data: {date_str}")
            return None

    def consultar_resultados(self, batch_size=20):
        docentes = self.search([('cod_prof', '!=', False)])
        
        if not docentes:
            raise ValueError("Nenhum docente com o campo 'cod_prof' preenchido foi encontrado.")

        total_docentes = len(docentes)
        _logger.info(f"Iniciando processamento para um total de {total_docentes} docentes em lotes de {batch_size}.")

        for start in range(0, total_docentes, batch_size):
            batch_docentes = docentes[start:start + batch_size]
            
            for docente in batch_docentes:
                try:
                    _logger.info(f"Consultando resultados para o docente '{docente.docente}' (cod_prof={docente.cod_prof}).")
                    resultado = self._make_api_request('EDUAPP02', docente.cod_prof)
                    _logger.debug(f"Resposta da API para o docente '{docente.docente}': {resultado}")
                    
                    if 'Row' in resultado and resultado['Row']:
                        resultado_data_list = resultado['Row']
                        _logger.info(f"Número de registros de resultados encontrados para o docente '{docente.docente}': {len(resultado_data_list)}")
                        for resultado_data in resultado_data_list:
                            self._create_or_update_resultado(resultado_data, docente)
                    else:
                        _logger.info(f"Nenhum resultado encontrado ou 'Row' não presente para o docente {docente.docente} com cod_prof {docente.cod_prof}")
                        
                except ValueError as e:
                    _logger.error(f"Erro ao consultar resultados para o docente {docente.docente}: {e}")

            self.env.cr.commit()
            _logger.info(f"Lote de {len(batch_docentes)} docentes processado com sucesso. Total processado: {start + len(batch_docentes)}/{total_docentes}")

        _logger.info("Processamento de todos os resultados concluído com sucesso.")

        # Adiciona a mensagem de sucesso
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sucesso',
                'message': 'Consulta de resultados concluída com sucesso.',
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_or_update_resultado(self, resultado_data, docente):
        resultados_model = self.env['blue.edu.resultados']
        
        resultado_record = resultados_model.search([
            ('id_turma_disc', '=', resultado_data['IDTURMADISC']),
            ('cod_docente', '=', resultado_data['CODPROF']),
            ('edu_id', '=', docente.id),
            ('aula', '=', resultado_data['AULA'])
        ], limit=1)

        dt_inicial = self._convert_date(resultado_data['DTINICIAL'])
        dt_final = self._convert_date(resultado_data['DTFINAL'])
        data_aula = self._convert_date(resultado_data['DATA_AULA'])

        values = {
            'edu_id': docente.id,
            'cod_docente': resultado_data['CODPROF'],
            'id_turma_disc': resultado_data['IDTURMADISC'],
            'dt_inicial': dt_inicial,
            'dt_final': dt_final,
            'unidade': resultado_data['UNIDADE'],
            'modalidade': resultado_data['MODALIDADE'],
            'curso': resultado_data['CURSO'],
            'disciplina': resultado_data['DISCIPLINA'],
            'cod_turma': resultado_data['CODTURMA'],
            'aula': resultado_data['AULA'],
            'data_aula': data_aula,
            'periodo_letivo': resultado_data['PERIODO_LETIVO']
        }

        if resultado_record:
            _logger.info(f"Atualizando resultado com ID {resultado_data['IDTURMADISC']} para o docente {docente.docente}")
            resultado_record.write(values)
        else:
            _logger.info(f"Criando resultado com ID {resultado_data['IDTURMADISC']} para o docente {docente.docente}")
            resultados_model.create(values)

    def _update_total_resultados(self, docente):
        total_resultados = self.env['blue.edu.resultados'].search_count([('edu_id', '=', docente.id)])
        docente.total_resultados = total_resultados
        _logger.info(f"Total de resultados atualizado para o docente {docente.docente}: {total_resultados}")

    def consultar_pendencias(self, batch_size=20):
        docentes = self.search([('cod_prof', '!=', False)])
        
        if not docentes:
            raise ValueError("Nenhum docente com o campo 'cod_prof' preenchido foi encontrado.")

        total_docentes = len(docentes)
        
        for start in range(0, total_docentes, batch_size):
            batch_docentes = docentes[start:start + batch_size]
            
            for docente in batch_docentes:
                try:
                    resultado = self._make_api_request('EDUAPP04', docente.cod_prof)
                    
                    if 'Row' in resultado and resultado['Row']:
                        resultado_data_list = resultado['Row']
                        for pendencia_data in resultado_data_list:
                            self._create_or_update_pendencia(pendencia_data, docente)
                    else:
                        _logger.info(f"Nenhuma pendência encontrada ou 'Row' não presente para o docente {docente.docente} com cod_prof {docente.cod_prof}")
                        
                except ValueError as e:
                    _logger.error(f"Erro ao consultar pendências para o docente {docente.docente}: {e}")

            self.env.cr.commit()
            _logger.info(f"Lote de {len(batch_docentes)} docentes processado com sucesso. Total processado: {start + len(batch_docentes)}/{total_docentes}")

        _logger.info("Processamento de todas as pendências concluído com sucesso.")

        # Adiciona a mensagem de sucesso
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sucesso',
                'message': 'Consulta de pendências concluída com sucesso.',
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_or_update_pendencia(self, pendencia_data, docente):
        pendencias_model = self.env['blue.edu.pendencias']
        
        pendencia_record = pendencias_model.search([
            ('cod_docente', '=', pendencia_data['CODPROF']),
            ('edu_id', '=', docente.id)
        ], limit=1)

        values = {
            'edu_id': docente.id,
            'cod_docente': pendencia_data['CODPROF'],
            'media_notas': pendencia_data['MEDIA_NOTAS'],
            'medias_faltas': pendencia_data['MEDIA_FALTAS'],
            'docente': pendencia_data['DOCENTE']
        }

        if pendencia_record:
            _logger.info(f"Atualizando pendência para o docente {pendencia_data['DOCENTE']} com cod_prof {pendencia_data['CODPROF']}")
            pendencia_record.write(values)
        else:
            _logger.info(f"Criando pendência para o docente {pendencia_data['DOCENTE']} com cod_prof {pendencia_data['CODPROF']}")
            pendencias_model.create(values)

    def _update_total_pendencias(self, docente):
        total_pendencias = self.env['blue.edu.pendencias'].search_count([('edu_id', '=', docente.id)])
        docente.total_pendencias = total_pendencias
        _logger.info(f"Total de pendências atualizado para o docente {docente.docente}: {total_pendencias}")

    def consultar_apuracoes(self, batch_size=20):
        docentes = self.search([('cod_prof', '!=', False)])
        
        if not docentes:
            raise ValueError("Nenhum docente com o campo 'cod_prof' preenchido foi encontrado.")

        total_docentes = len(docentes)
        
        for start in range(0, total_docentes, batch_size):
            batch_docentes = docentes[start:start + batch_size]
            
            for docente in batch_docentes:
                try:
                    resultado = self._make_api_request('EDUAPP03', docente.cod_prof)
                    
                    _logger.info(f"Resposta da API para o docente {docente.docente} com cod_prof {docente.cod_prof}: {resultado}")

                    if 'Row' in resultado and resultado['Row']:
                        resultado_data_list = resultado['Row']
                        for apuracao_data in resultado_data_list:
                            self._create_or_update_apuracao(apuracao_data, docente)

                        self._update_total_apuracoes(docente)
                    else:
                        _logger.info(f"Nenhuma apuração encontrada ou 'Row' não presente para o docente {docente.docente} com cod_prof {docente.cod_prof}")
                        
                except ValueError as e:
                    _logger.error(f"Erro ao consultar apurações para o docente {docente.docente}: {e}")

            self.env.cr.commit()
            _logger.info(f"Lote de {len(batch_docentes)} docentes processado com sucesso. Total processado: {start + len(batch_docentes)}/{total_docentes}")

        _logger.info("Processamento de todas as apurações concluído com sucesso.")

        # Adiciona a mensagem de sucesso
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sucesso',
                'message': 'Consulta de apurações concluída com sucesso.',
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_or_update_apuracao(self, apuracao_data, docente):
        apuracao_model = self.env['blue.edu.apuracao']
        
        apuracao_record = apuracao_model.search([
            ('idturmadisc', '=', apuracao_data['IDTURMADISC']),
            ('codprof', '=', apuracao_data['CODPROF']),
            ('edu_id', '=', docente.id)
        ], limit=1)

        dtinicial = self._convert_date(apuracao_data['DTINICIAL'])
        dtfinal = self._convert_date(apuracao_data['DTFINAL'])

        values = {
            'edu_id': docente.id,
            'idturmadisc': apuracao_data['IDTURMADISC'],
            'dtinicial': dtinicial,
            'dtfinal': dtfinal,
            'unidade': apuracao_data['UNIDADE'],
            'modalidade': apuracao_data['MODALIDADE'],
            'curso': apuracao_data['CURSO'],
            'disciplina': apuracao_data['DISCIPLINA'],
            'codturma': apuracao_data['CODTURMA'],
            'codprof': apuracao_data['CODPROF'],
            'docente': apuracao_data['DOCENTE'],
            'tipo_docente': apuracao_data['TIPO_DOCENTE'],
            'periodo_letivo': apuracao_data['PERIODO_LETIVO'],
        }

        if apuracao_record:
            _logger.info(f"Atualizando apuração para o docente {apuracao_data['DOCENTE']} na turma/disciplina {apuracao_data['IDTURMADISC']}")
            apuracao_record.write(values)
        else:
            _logger.info(f"Criando apuração para o docente {apuracao_data['DOCENTE']} na turma/disciplina {apuracao_data['IDTURMADISC']}")
            apuracao_model.create(values)

    def _update_total_apuracoes(self, docente):
        total_apuracoes = self.env['blue.edu.apuracao'].search_count([('edu_id', '=', docente.id)])
        docente.total_apuracao = total_apuracoes
        _logger.info(f"Total de apurações atualizado para o docente {docente.docente}: {total_apuracoes}")

     
    def _create_or_update_desempenho(self, desempenho_data, docente):
        """
        Função para criar ou atualizar os registros de satisfação do docente.
        """
        desempenho_model = self.env['blue.edu.desempenho']

        # Procura o registro de satisfação com base no ID da turma/disciplina e código do docente
        desempenho_record = desempenho_model.search([
            ('id_turma_disc', '=', desempenho_data['IDTURMADISC']),
            ('cod_docente', '=', desempenho_data['CODPROF']),
            ('edu_id', '=', docente.id)
        ], limit=1)

        values = {
            'edu_id': docente.id,
            'cod_docente': desempenho_data['CODPROF'],
            'docente': desempenho_data['DOCENTE'],
            'percentual_desempenho_docente': desempenho_data['%_DESEMPENHO_DOCENTE'],
            'unidade': desempenho_data['UNIDADE'],
            'modalidade': desempenho_data['MODALIDADE'],
            'curso': desempenho_data['CURSO'],
            'disciplina': desempenho_data['DISCIPLINA'],
            'id_turma_disc': desempenho_data['IDTURMADISC'],
            'cod_turma': desempenho_data['CODTURMA'],
            'tipo_turma': desempenho_data['TIPO_TURMA'],
            'ano': desempenho_data['ANO'],
        }

        if desempenho_record:
            _logger.info(f"Atualizando satisfação para o docente {desempenho_data['DOCENTE']} na turma/disciplina {desempenho_data['IDTURMADISC']}")
            desempenho_record.write(values)
        else:
            _logger.info(f"Criando satisfação para o docente {desempenho_data['DOCENTE']} na turma/disciplina {desempenho_data['IDTURMADISC']}")
            desempenho_model.create(values)

    def consultar_desempenho(self, batch_size=5):
        """
        Consulta os dados de satisfação dos docentes em lotes, chamando a API EDUAPP05.
        """
        docentes = self.search([('cod_prof', '!=', False)])

        if not docentes:
            raise ValueError("Nenhum docente com o campo 'cod_prof' preenchido foi encontrado.")

        total_docentes = len(docentes)
        _logger.info(f"Iniciando processamento para um total de {total_docentes} docentes em lotes de {batch_size}.")

        for start in range(0, total_docentes, batch_size):
            batch_docentes = docentes[start:start + batch_size]

            for docente in batch_docentes:
                try:
                    _logger.info(f"Consultando satisfação para o docente '{docente.docente}' (cod_prof={docente.cod_prof}).")
                    resultado = self._make_api_request('EDUAPP05', docente.cod_prof)
                    _logger.debug(f"Resposta da API para o docente '{docente.docente}': {resultado}")

                    if 'Row' in resultado and resultado['Row']:
                        resultado_data_list = resultado['Row']
                        _logger.info(f"Número de registros de satisfação encontrados para o docente '{docente.docente}': {len(resultado_data_list)}")
                        for desempenho_data in resultado_data_list:
                            self._create_or_update_desempenho(desempenho_data, docente)
                    else:
                        _logger.info(f"Nenhuma satisfação encontrada ou 'Row' não presente para o docente {docente.docente} com cod_prof {docente.cod_prof}")

                except ValueError as e:
                    _logger.error(f"Erro ao consultar satisfação para o docente {docente.docente}: {e}")

            self.env.cr.commit()
            _logger.info(f"Lote de {len(batch_docentes)} docentes processado com sucesso. Total processado: {start + len(batch_docentes)}/{total_docentes}")

        _logger.info("Processamento de toda a satisfação concluído com sucesso.")

        # Adiciona a mensagem de sucesso
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sucesso',
                'message': 'Consulta de satisfação concluída com sucesso.',
                'type': 'success',
                'sticky': False,
            }
        }

       # Métodos compute (se necessários)
    @api.depends('modalidade')
    def _compute_total_apuracao(self):
        for record in self:
            record.total_apuracao = len(record.modalidade)

    @api.depends('pesquisas')
    def _compute_total_pesquisas(self):
        for record in self:
            record.total_pesquisas = len(record.pesquisas)

    @api.depends('id_turma')
    def _compute_total_resultados(self):
        for record in self:
            record.total_resultados = len(record.id_turma)

    @api.depends('cod_docente')
    def _compute_total_pendencias(self):
        for record in self:
            record.total_pendencias = len(record.cod_docente)
    @api.model
    def action_consultar_docentes(self):
        # Chama a função de consulta de docentes
        return self.consultar_docentes()

    @api.model
    def action_consultar_pesquisas(self):
        # Chama a função de consulta de pesquisas
        return self.consultar_pesquisas()

    @api.model
    def action_consultar_resultados(self):
        # Chama a função de consulta de resultados
        return self.consultar_resultados()

    @api.model
    def action_consultar_pendencias(self):
        # Chama a função de consulta de pendências
        return self.consultar_pendencias()

    @api.model
    def action_consultar_apuracoes(self):
        # Chama a função de consulta de apurações
        return self.consultar_apuracoes()


