from odoo import http
from odoo.http import request, Response
from datetime import datetime
import json
import logging

_logger = logging.getLogger(__name__)

def convert_datetime_to_string(obj):
    """ Helper function to convert datetime objects to a string representation """
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d")  # Adjust the format as needed
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def convert_nested_dicts(data):
    """ Convert all datetime objects in a nested dictionary structure to strings """
    if isinstance(data, dict):
        return {key: convert_nested_dicts(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_nested_dicts(element) for element in data]
    elif isinstance(data, datetime):
        return data.strftime("%Y-%m-%d")
    else:
        return data

class BlueEduWebsite(http.Controller):

    @http.route('/indicador', type='http', auth="user", website=True)
    def indicador(self, **kwargs):
        user = request.env.user
        edu_records = request.env['blue.edu'].search([('user_id', '=', user.id)])
        pesquisas = request.env['blue.edu.pesquisas'].search([('edu_id', 'in', edu_records.ids)])
        
        # Fetching related data from blue.edu.resultados to include dt_final
        resultados = request.env['blue.edu.resultados'].search([('edu_id', 'in', edu_records.ids)])
        desempenho_records = request.env['blue.edu.desempenho'].search([('edu_id', 'in', edu_records.ids)])

        # Criar um dicionário para armazenar os dados de satisfação por `id_turma_disc`
        desempenho_data = {}
        for record in desempenho_records:
            if record.id_turma_disc not in desempenho_data:
                desempenho_data[record.id_turma_disc] = {
                    'docente': record.docente,
                    'percentual_desempenho': record.percentual_desempenho_docente,
                    'unidade': record.unidade,
                    'modalidade': record.modalidade,
                    'curso': record.curso,
                    'disciplina': record.disciplina,
                    'cod_turma': record.cod_turma,
                    'tipo_turma': record.tipo_turma,
                    'ano': record.ano
                }


        # Calculando a média de notas e faltas
        pendencias = request.env['blue.edu.pendencias'].search([('edu_id', 'in', edu_records.ids)])
        media_notas = sum(pendencia.media_notas for pendencia in pendencias) / len(pendencias) if pendencias else 0
        media_faltas = sum(pendencia.medias_faltas for pendencia in pendencias) / len(pendencias) if pendencias else 0
        
        
        # Calculando os totais
        total_apuracao = sum(edu.total_apuracao for edu in edu_records)
        total_pesquisas = sum(edu.total_pesquisas for edu in edu_records)
        total_resultados = sum(edu.total_resultados for edu in edu_records)
        total_pendencias = sum(edu.total_pendencias for edu in edu_records)
        total_aulas = 0

        # Calculando os totais agrupados por disciplina
        disciplina_data = {}
        for pesquisa in pesquisas:
            if pesquisa.disciplina not in disciplina_data:
                disciplina_data[pesquisa.disciplina] = {
                    'pesquisas': 0,
                    'respondidas': 0,
                    'percentual_respondidas': 0.0
                }
            disciplina_data[pesquisa.disciplina]['pesquisas'] += pesquisa.pesquisas
            disciplina_data[pesquisa.disciplina]['respondidas'] += pesquisa.respondidas
            disciplina_data[pesquisa.disciplina]['percentual_respondidas'] += pesquisa.percentual_respondidas

         # Create a mapping of turma_disc -> data_final, dt_inicial, modalidade, periodo_letivo, and aulas from os resultados
        resultados_mapping = {
            resultado.id_turma_disc: {
                'dt_final': resultado.dt_final.strftime("%Y-%m-%d") if resultado.dt_final else '--',
                'dt_inicial': resultado.dt_inicial.strftime("%Y-%m-%d") if resultado.dt_inicial else '--',
                'modalidade': resultado.modalidade or 'N/A',
                'periodo_letivo': resultado.periodo_letivo or 'N/A',
                'aulas': resultado.aula or 0
            }
            for resultado in resultados
        }                                      

        # Agrupando por cod_turma e id_turma_disc
        turma_data = {}
        for pesquisa in pesquisas:
            if pesquisa.cod_turma not in turma_data:
                turma_data[pesquisa.cod_turma] = {}
            if pesquisa.id_turma_disc not in turma_data[pesquisa.cod_turma]:
                unidade = pesquisa.unidade if pesquisa.unidade else 'N/A'
                # Fetch dt_final, dt_inicial, modalidade, periodo_letivo, aulas from resultados_mapping
                resultado_info = resultados_mapping.get(pesquisa.id_turma_disc, {})
                dt_final = resultado_info.get('dt_final', '--')
                dt_inicial = resultado_info.get('dt_inicial', '--')
                modalidade = pesquisa.modalidade or resultado_info.get('modalidade', 'N/A')
                periodo_letivo = resultado_info.get('periodo_letivo', 'N/A')
                aulas_raw = resultado_info.get('aulas', 0)

                # Ensure 'aulas' is an integer
                try:
                    aulas = int(aulas_raw)
                except (TypeError, ValueError):
                    _logger.warning(f"Invalid 'aulas' value for id_turma_disc {pesquisa.id_turma_disc}: {aulas_raw}")
                    aulas = 0  # Assign a default value to aulas

                # Now 'aulas' is safely assigned and can be used
                # Increment the total_aulas
                total_aulas += aulas

                turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc] = {
                    'pesquisas': 0,
                    'respondidas': 0,
                    'percentual_respondidas': 0.0,
                    'disciplinas': {},
                    'unidade': unidade,
                    'dt_inicial': dt_inicial,
                    'dt_final': dt_final,
                    'modalidade': modalidade,
                    'periodo_letivo': periodo_letivo,
                    'aulas': aulas  # Adicionando aulas aqui
                }

            # Incrementing overall values for the turma_disc    
            turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['pesquisas'] += pesquisa.pesquisas
            turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['respondidas'] += pesquisa.respondidas
            turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['percentual_respondidas'] += pesquisa.percentual_respondidas

            # Handling the discipline-specific details
            if pesquisa.disciplina not in turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['disciplinas']:
                turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['disciplinas'][pesquisa.disciplina] = {
                    'pesquisas': 0,
                    'respondidas': 0,
                    'percentual_respondidas': 0.0,
                    'dt_inicial': turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['dt_inicial'],
                    'dt_final': turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['dt_final'],
                    'aulas': turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['aulas']  # Include aulas here
                }

            turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['disciplinas'][pesquisa.disciplina]['pesquisas'] += pesquisa.pesquisas
            turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['disciplinas'][pesquisa.disciplina]['respondidas'] += pesquisa.respondidas
            turma_data[pesquisa.cod_turma][pesquisa.id_turma_disc]['disciplinas'][pesquisa.disciplina]['percentual_respondidas'] += pesquisa.percentual_respondidas

        # After total_aulas calculation
        total_aulas = int(total_aulas)  # Ensure total_aulas is an integer
        _logger.info(f"Total aulas calculated: {total_aulas}")

        # Convertendo todos os objetos datetime em strings na estrutura do dicionário `turma_data`
        turma_data = convert_nested_dicts(turma_data)

        # Convertendo turma_data para uma lista de tuplas para facilitar a iteração no template
        turma_data_list = [(k, v) for k, v in turma_data.items()]

        # Convertendo turma_data para JSON para uso em JavaScript
        turma_data_json = json.dumps(turma_data)

        return request.render('blue_edu_website.indicador_page', {
            'edu_records': edu_records,
            'pesquisas': pesquisas,
            'desempenho_data': desempenho_data,  # Passando os dados de satisfação para o template
            'media_notas': media_notas,
            'media_faltas': media_faltas,
            'disciplina_data': disciplina_data,
            'turma_data': turma_data_json,  # Passando o JSON string para uso em JavaScript
            'turma_data_list': turma_data_list,  # Passando a lista de tuplas para iteração no template
            'total_apuracao': total_apuracao,
            'total_pesquisas': total_pesquisas,
            'total_resultados': total_resultados,
            'total_pendencias': total_pendencias,
            'total_aulas': total_aulas  
        })

    '''@http.route('/indicador/data', type='json', auth="user", methods=['GET'], website=True)
    def indicador_data(self, **kwargs):
        user = request.env.user
        edu_records = request.env['blue.edu'].search_read([('user_id', '=', user.id)], [
            'unidade', 'disciplina', 'percentual_respondidas', 'pesquisas', 'respondidas', 'cod_turma', 'cod_prof', 'conteudo_efetivo'
        ])
        return edu_records'''

    @http.route('/indicadores/data', type='json', auth="user")
    def indicador_data(self):
        user = request.env.user
        edu_records = request.env['blue.edu'].search([('user_id', '=', user.id)])
        data = [{
            'unidade': record.unidade,
            'disciplina': record.disciplina,
            'percentual_respondidas': record.percentual_respondida,
            'pesquisas': record.pesquisas,
            'respondidas': record.respondidas,
            'cod_turma': record.cod_turma,
            'cod_prof': record.cod_prof,
            'conteudo_efetivo': record.conteudo_efetivo
        } for record in edu_records]
        return Response(json.dumps({'data': data}), content_type='application/json')

        @http.route('/indicador/data', type='json', auth="user", methods=['GET'], website=True, csrf=False)
        def indicador_data(self, **kwargs):
            user = request.env.user
            try:
                user_id = user.id
                _logger.info(f"Fetching data for user ID: {user_id}")

                # Buscar os registros do modelo blue.edu
                edu_records = request.env['blue.edu'].search_read([('user_id', '=', user_id)], [
                    'unidade', 'disciplina', 'percentual_respondidas', 'pesquisas', 'respondidas', 'cod_turma', 'cod_prof', 'conteudo_efetivo'
                ])

                # Buscar os registros de satisfação no modelo blue.edu.desempenho
                desempenho_records = request.env['blue.edu.desempenho'].search_read([('edu_id', 'in', [rec['id'] for rec in edu_records])], [
                    'edu_id', 'cod_docente', 'docente', 'percentual_desempenho_docente', 'unidade', 'disciplina', 'cod_turma', 'ano'
                ])

                # Organizar os dados de satisfação por 'edu_id' para fácil acesso
                desempenho_data = {}
                for record in desempenho_records:
                    desempenho_data[record['edu_id'][0]] = {
                        'docente': record['docente'],
                        'percentual_desempenho': record['percentual_desempenho_docente'],
                        'unidade': record['unidade'],
                        'disciplina': record['disciplina'],
                        'cod_turma': record['cod_turma'],
                        'ano': record['ano'],
                    }

                # Adicionando os dados de satisfação no resultado dos registros educacionais
                for edu in edu_records:
                    edu['percentual_desempenho_docente'] = desempenho_data.get(edu['id'], {}).get('percentual_desempenho', 0)

                response_data = {'data': edu_records}

                _logger.info(f"Data fetched successfully for user ID: {user_id} - Data: {response_data}")
                return request.make_response(json.dumps(response_data), headers={'Content-Type': 'application/json'})
            except Exception as e:
                error_message = json.dumps({'error': str(e)})
                _logger.error(f"Error fetching data for user ID {user_id}: {str(e)}")
                return request.make_response(error_message, status=400, headers={'Content-Type': 'application/json'})


        class CustomController(http.Controller):
            @http.route('/api/indicadores', type='json', auth="user", methods=['GET'], csrf=False)
            def indicadores_data(self, **kwargs):
                user = request.env.user
                try:
                    user_id = user.id
                    _logger.info(f"Fetching data for user ID: {user_id}")

                    edu_records = request.env['blue.edu'].search_read([('user_id', '=', user_id)], [
                        'unidade', 'disciplina', 'percentual_respondidas', 'pesquisas', 'respondidas', 'cod_turma', 'cod_prof', 'conteudo_efetivo'
                    ])
                    response_data = {'data': edu_records}
                    return Response(json.dumps(response_data), content_type='application/json')
                except Exception as e:
                    error_message = json.dumps({'error': str(e)})
                    _logger.error(f"Error fetching data for user ID {user_id}: {str(e)}")
                    return Response(error_message, status=400, content_type='application/json')

