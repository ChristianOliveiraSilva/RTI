from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mato Grosso do Sul: UTC-4 (sem horario de verao no Brasil vigente a partir de 2019)
_MS_TZ = timezone(timedelta(hours=-4), "GMT-4")

PI_TYPE_LABELS = {
    "software": "Programa de Computador (Software)",
    "patente": "Patente",
    "desenho_industrial": "Desenho Industrial",
    "marca": "Marca",
    "cultivar": "Cultivar",
    "topografia": "Topografia de Circuitos",
    "outro": "Outro",
}

IFMS_BOND_LABELS = {
    "servidor": "Servidor",
    "estudante": "Estudante",
    "outros": "Outros",
}

IFMS_CAMPUSES = [
    "Aquidauana",
    "Campo Grande",
    "Corumbá",
    "Coxim",
    "Dourados",
    "Jardim",
    "Naviraí",
    "Nova Andradina",
    "Ponta Porã",
    "Três Lagoas",
]

APPLICATION_FIELDS = [
    "AD01 - Administração (desenvolv. organizacional, desburocratização)",
    "AD02 - Função Administrativa (Planejamento governamental)",
    "AD03 - Modernização Administrativa (análise organizacional, O&M)",
    "AD04 - Administração Pública",
    "AD05 - Administração de Empresas",
    "AD06 - Administração da Produção",
    "AD07 - Administração de Pessoal",
    "AD08 - Administração de Material",
    "AD09 - Administração Patrimonial",
    "AD10 - Marketing (mercadologia)",
    "AD11 - Administração de Escritório",
    "AG01 - Agricultura (agropecuária, desenvolvimento rural)",
    "AG02 - Ciências Agrárias",
    "AG03 - Administração Agrícola",
    "AG04 - Economia Agrícola",
    "AG05 - Sistemas Agrícolas",
    "AG06 - Engenharia Agrícola",
    "AG07 - Edafologia (conservação de solo)",
    "AG08 - Fitopatologia (doenças e pragas vegetais)",
    "AG09 - Produção Vegetal",
    "AG10 - Produção Animal",
    "AG11 - Ciências Florestais",
    "AG12 - Aquacultura",
    "AG13 - Extrativismo Vegetal",
    "AG14 - Extrativismo Animal",
    "AN01 - Sociedade (sistema social)",
    "AN02 - Desenvolvimento Social",
    "AN03 - Grupos Sociais",
    "AN04 - Cultura (civilização, cultura popular)",
    "AN05 - Religião",
    "AN06 - Antropologia",
    "AN07 - Sociologia",
    "AH01 - Assentamentos Humanos",
    "AH02 - Cidade (metrópole, região metropolitana)",
    "AH03 - Organização Territorial",
    "AH04 - Políticas de Assentamentos Humanos",
    "AH05 - População",
    "AH06 - Disciplinas Auxiliares (demografia)",
    "BL01 - Biologia",
    "BL02 - Genética",
    "BL03 - Citologia (biologia celular)",
    "BL04 - Microbiologia",
    "BL05 - Anatomia",
    "BL06 - Fisiologia",
    "BL07 - Bioquímica",
    "BL08 - Biofísica",
    "BT01 - Botânica",
    "BT02 - Fitogeografia",
    "BT03 - Botânica Econômica",
    "BT04 - Botânica Sistemática",
    "CO01 - Filosofia",
    "CO02 - Ciência",
    "CO03 - Ciências Linguísticas",
    "CO04 - Comunicação",
    "CO05 - Arte",
    "CO06 - História",
    "CC01 - Construção Civil",
    "CC02 - Processo Construtivo",
    "CC03 - Organização da Construção",
    "CC04 - Obra Pública",
    "CC05 - Estrutura (cálculo estrutural)",
    "CC06 - Edificação",
    "CC07 - Tecnologia da Construção",
    "CC08 - Higiene das Construções",
    "CC09 - Engenharia Hidráulica",
    "CC10 - Solo (mecânica dos solos)",
    "DI01 - Legislação",
    "DI02 - Direito Constitucional",
    "DI03 - Outras Disciplinas do Direito",
    "EL01 - Ecologia",
    "EL02 - Ecofisiologia",
    "EL03 - Ecologia Humana",
    "EL04 - Ecologia Vegetal/Animal",
    "EL05 - Etologia",
    "EC01 - Economia",
    "EC02 - Análise Microeconômica",
    "EC03 - Teoria Macroeconômica",
    "EC04 - Atividade Econômica",
    "EC05 - Contabilidade Nacional",
    "EC06 - Economia Monetária",
    "EC07 - Mercado",
    "EC08 - Bens Econômicos",
    "EC09 - Engenharia/Dinâmica Econômica",
    "EC10 - Economia Especial (regional)",
    "EC11 - Propriedade",
    "EC12 - Economia Internacional",
    "EC13 - Política Econômica",
    "EC14 - Empresa",
    "ED01 - Ensino Regular",
    "ED02 - Ensino Supletivo",
    "ED03 - Administração/Processo de Ensino",
    "ED04 - Formas de Ensino/Material Instrucional",
    "ED05 - Currículo",
    "ED06 - Educação (pedagogia)",
    "EN01 - Energia",
    "EN02 - Recursos/Serviços/Formas de Energia",
    "EN03 - Combustível",
    "EN04 - Tecnologia e Energia",
    "EN05 - Engenharia Eletrônica",
    "EN06 - Engenharia Nuclear",
    "FN01 - Finanças Públicas",
    "FN02 - Finanças Privadas",
    "FN03 - Sistema Financeiro",
    "FN04 - Recursos/Orçamento/Instrumentos",
    "FN05 - Administração Financeira",
    "FN06 - Contabilidade",
    "FQ01 - Matéria/Física das Partículas",
    "FQ02 - Acústica/Óptica",
    "FQ03 - Onda",
    "FQ04 - Metrologia",
    "FQ05 - Mecânica",
    "FQ06 - Física dos Sólidos/Fluídos/Plasmas",
    "FQ07 - Termodinâmica",
    "FQ08 - Eletrônica",
    "FQ09 - Magnetismo/Eletromagnetismo",
    "FQ10 - Física de Superfície/Dispersão",
    "FQ11 - Radiação",
    "FQ12 - Espectroscopia",
    "FQ13 - Física Molecular/Atômica",
    "FQ14 - Química",
    "FQ15 - Química Analítica/dos Polímeros",
    "FQ16 - Físico-Química",
    "FQ17 - Química Orgânica",
    "FQ18 - Química Inorgânica",
    "GC01 - Geografia Física",
    "GC02 - Geografia Humana",
    "GC03 - Geografia Regional",
    "GC04 - Orientação Geográfica",
    "GC05 - Geodesia",
    "GC06 - Topografia",
    "GC07 - Fotogrametria",
    "GC08 - Mapeamento",
    "GC09 - Métodos e Processos de Cartografia",
    "GC10 - Plano Cartográfico",
    "GL01 - Geologia Física",
    "GL02 - Glaciologia",
    "GL03 - Geotectônica",
    "GL04 - Geologia Marinha",
    "GL05 - Geologia Histórica",
    "GL06 - Geologia Econômica",
    "GL07 - Geoquímica/Hidrogeologia/Geofísica/Geotécnica",
    "HB01 - Habitação",
    "HB02 - Tipologia Habitacional",
    "HD01 - Hidrologia",
    "HD02 - Hidrografia",
    "HD03 - Hidrometria",
    "HD04 - Oceanografia",
    "IN01 - Indústria",
    "IN02 - Tecnologia",
    "IN03 - Engenharia",
    "IN04 - Indústria Extrativa Mineral",
    "IN05 - Indústria de Transformação",
    "IF01 - Informação",
    "IF02 - Documentação",
    "IF03 - Reprografia",
    "IF04 - Documento",
    "IF05 - Biblioteconomia",
    "IF06 - Arquivologia",
    "IF07 - Ciência da Informação",
    "IF08 - Serviço de Informação",
    "IF09 - Uso da Informação",
    "IF10 - Genérico (processamento de dados)",
    "MT01 - Lógica Matemática",
    "MT02 - Álgebra",
    "MT03 - Geometria",
    "MT04 - Análise Matemática",
    "MT05 - Cálculo",
    "MT06 - Matemática Aplicada",
    "MA01 - Meio Ambiente",
    "MA02 - Recursos Naturais",
    "MA03 - Poluição",
    "MA04 - Qualidade Ambiental",
    "ME01 - Meteorologia",
    "ME02 - Atmosfera",
    "ME03 - Climatologia",
    "PD01 - Pedologia (ciência do solo)",
    "PD02 - Pedogênese",
    "PD03 - Tipos de Solo",
    "PL01 - Ciência Política",
    "PL02 - Política",
    "PR01 - Previdência",
    "PR02 - Benefícios Previdenciários",
    "PR03 - Assistência Social",
    "PS01 - Psicologia",
    "PS02 - Comportamento",
    "PS03 - Teoria Psicológica",
    "SM01 - Saneamento",
    "SM02 - Resíduo",
    "SM03 - Limpeza",
    "SM04 - Abastecimento de Água",
    "SM05 - Esgoto",
    "SD01 - Saúde",
    "SD02 - Administração Sanitária",
    "SD03 - Doença",
    "SD04 - Deficiência Física",
    "SD05 - Assistência Médica",
    "SD06 - Terapia e Diagnóstico",
    "SD07 - Medicina",
    "SD08 - Especialidades Médicas",
    "SD09 - Engenharia Biomédica",
    "SD10 - Farmacologia",
    "SD11 - Odontologia",
    "SV01 - Serviços",
    "SV02 - Seguro",
    "SV03 - Comércio",
    "SV04 - Turismo",
    "TC01 - Telecomunicações",
    "TC02 - Sistemas de Telecomunicações",
    "TC03 - Engenharia de Telecomunicações",
    "TC04 - Serviços/Redes de Telecomunicações",
    "TB01 - Trabalho",
    "TB02 - Recursos Humanos",
    "TB03 - Mercado de Trabalho",
    "TB04 - Condições de Trabalho",
    "TB05 - Estrutura Ocupacional",
    "TB06 - Lazer",
    "TP01 - Transporte",
    "TP02 - Sistemas de Transporte",
    "TP03 - Serviços de Transporte",
    "TP04 - Engenharia de Transporte",
    "TP05 - Modalidades de Transporte",
    "UB01 - Urbanismo",
    "UB02 - Solo Urbano",
    "UB03 - Área Urbana",
    "UB04 - Circulação Urbana",
    "UB05 - Arquitetura",
]

PROGRAM_TYPES = [
    "SO01 - Sistema Operacional",
    "SO02 - Interface de Entrada e Saída",
    "SO03 - Interface Básica de Disco",
    "SO04 - Interface de Comunicação",
    "SO05 - Gerenciador de Usuários",
    "SO06 - Administrador de Dispositivos",
    "SO07 - Controlador de Processos",
    "SO08 - Controlador de Redes",
    "SO09 - Processador de Comandos",
    "LG01 - Linguagens",
    "LG02 - Compilador",
    "LG03 - Montador",
    "LG04 - Pré-Compilador",
    "LG05 - Compilador Cruzado",
    "LG06 - Pré-Processador",
    "LG07 - Interpretador",
    "LG08 - Linguagem Procedural",
    "LG09 - Linguagem Não Procedural",
    "GI01 - Gerenciador de Informações",
    "GI02 - Gerenciador de Banco de Dados",
    "GI03 - Gerador de Telas",
    "GI04 - Gerador de Relatórios",
    "GI05 - Dicionário de Dados",
    "GI06 - Entrada e Validação de Dados",
    "GI07 - Organização/Tratamento/Manutenção de Arquivos",
    "GI08 - Recuperação de Dados",
    "CD01 - Comunicação de Dados",
    "CD02 - Emuladores de Terminais",
    "CD03 - Monitores de Teleprocessamento",
    "CD04 - Gerenciador de Dispositivos e Periféricos",
    "CD05 - Gerenciador de Rede de Comunicação de Dados",
    "CD06 - Rede Local",
    "FA01 - Ferramenta de Apoio",
    "FA02 - Processadores de Texto",
    "FA03 - Planilhas Eletrônicas",
    "FA04 - Geradores de Gráficos",
    "DS01 - Ferramentas de Suporte ao Desenvolvimento de Sistemas",
    "DS02 - Gerador de Aplicações",
    "DS03 - CASE (Computer Aided Software Engineering)",
    "DS04 - Desenvolvimento com Metodologia",
    "DS05 - Bibliotecas de Rotinas",
    "DS06 - Apoio à Programação",
    "DS07 - Suporte à Documentação",
    "DS08 - Conversor de Sistemas",
    "AV01 - Avaliação de Desempenho",
    "AV02 - Contabilização de Recursos",
    "PD01 - Segurança e Proteção de Dados",
    "PD02 - Senha",
    "PD03 - Criptografia",
    "PD04 - Manutenção da Integridade dos Dados",
    "PD05 - Controle de Acessos",
    "SM01 - Simulação e Modelagem",
    "SM02 - Simulador (Voo/Carro/Submarino)",
    "SM03 - Simuladores de Ambiente Operacional",
    "SM04 - CAE/CAD/CAM/CAL/CBT",
    "IA01 - Inteligência Artificial",
    "IA02 - Sistemas Especialistas",
    "IA03 - Processamento de Linguagem Natural",
    "IT01 - Instrumentação",
    "IT02 - Instrumentação de Teste e Medição",
    "IT03 - Instrumentação Biomédica",
    "IT04 - Instrumentação Analítica",
    "AT01 - Automação",
    "AT02 - Automação de Escritório",
    "AT03 - Automação Comercial",
    "AT04 - Automação Bancária",
    "AT05 - Automação Industrial",
    "AT06 - Controle de Processos",
    "AT07 - Automação da Manufatura (CNC, Robótica)",
    "AT08 - Eletrônica Automotiva",
    "TI01 - Teleinformática",
    "TI02 - Terminais",
    "TI03 - Transmissão de Dados",
    "TI04 - Comutação de Dados",
    "CT01 - Comutação Telefônica e Telegráfica",
    "CT02 - Implementador de Funções Adicionais",
    "CT03 - Gerenciador de Operação e Manutenção",
    "CT04 - Terminal de Operação e Manutenção de Central",
    "UT01 - Utilitários",
    "UT02 - Compressor de Dados",
    "UT03 - Conversor de Meios de Armazenamento",
    "UT04 - Classificador/Intercalador",
    "UT05 - Controlador de Spool",
    "UT06 - Transferência de Arquivos",
    "AP01 - Aplicativo",
    "AP02 - Planejamento",
    "AP03 - Controle",
    "AP04 - Auditoria",
    "AP05 - Contabilização",
    "TC01 - Aplicações Técnico-Científicas",
    "TC02 - Pesquisa Operacional",
    "TC03 - Reconhecimento de Padrões",
    "TC04 - Processamento de Imagem",
    "ET01 - Entretenimento",
    "ET02 - Jogos Animados (arcade games)",
    "ET03 - Geradores de Desenhos",
    "ET04 - Simuladores Destinados ao Lazer",
]

STATUS_LABELS = {
    "draft": "Rascunho",
    "awaiting_authors": "Aguardando coautores",
    "awaiting_signatures": "Aguardando assinaturas",
    "awaiting_corrections": "Aguardando correções",
    "completed": "Concluído",
    "pending": "Pendente",
}


def format_date(value: Any, fmt: str = "%d/%m/%Y") -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, date):
        return value.strftime(fmt)
    return str(value)


def format_datetime(value: Any, fmt: str = "%d/%m/%Y %H:%M") -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        # Exibição padrão do sistema: fuso de MS (UTC-4)
        # Se vier sem tzinfo, assume UTC (como no banco) antes de converter.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(_MS_TZ).strftime(fmt)
    return str(value)


def format_datetime_ms(value: Any, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Data/hora no fuso de MS (UTC-4), ex. e-mail e prazo de convite."""
    if value is None:
        return ""
    if not isinstance(value, datetime):
        return str(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_MS_TZ).strftime(fmt)


def format_date_ms(value: Any, fmt: str = "%d/%m/%Y") -> str:
    """Data no fuso de MS (UTC-4), sem horário."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(_MS_TZ).strftime(fmt)
    if isinstance(value, date):
        return value.strftime(fmt)
    return str(value)


def format_percent(value: Any) -> str:
    if value is None:
        return "0%"
    try:
        return f"{float(value):.2f}".rstrip("0").rstrip(".") + "%"
    except (TypeError, ValueError):
        return f"{value}%"


def status_label(value: Any) -> str:
    if value is None:
        return ""
    key = value.value if hasattr(value, "value") else str(value)
    return STATUS_LABELS.get(key, key)


def pi_type_label(value: Any) -> str:
    if value is None:
        return ""
    key = value.value if hasattr(value, "value") else str(value)
    return PI_TYPE_LABELS.get(key, key)


def ifms_bond_label(value: Any) -> str:
    if value is None:
        return ""
    key = value.value if hasattr(value, "value") else str(value)
    return IFMS_BOND_LABELS.get(key, key)


templates.env.filters["fdate"] = format_date
templates.env.filters["fdatetime"] = format_datetime
templates.env.filters["fdatetime_ms"] = format_datetime_ms
templates.env.filters["fdate_ms"] = format_date_ms
templates.env.filters["fpercent"] = format_percent
templates.env.filters["status_label"] = status_label
templates.env.filters["pi_type_label"] = pi_type_label
templates.env.filters["ifms_bond_label"] = ifms_bond_label

templates.env.globals["PI_TYPE_LABELS"] = PI_TYPE_LABELS
templates.env.globals["IFMS_BOND_LABELS"] = IFMS_BOND_LABELS
templates.env.globals["IFMS_CAMPUSES"] = IFMS_CAMPUSES
templates.env.globals["APPLICATION_FIELDS"] = APPLICATION_FIELDS
templates.env.globals["PROGRAM_TYPES"] = PROGRAM_TYPES
templates.env.globals["STATUS_LABELS"] = STATUS_LABELS
