"""
Simulador e Apurador de Imposto de Renda Pessoa Física (IRPF)
Autor: Wendel Vieira
Projeto: Organizador e Simulador de Declaração de IRPF no Excel & Python
"""

import argparse
import json
import csv
import sys
from dataclasses import dataclass, asdict
from typing import Dict, Any, List

# Constantes e Parâmetros Oficiais da Receita Federal do Brasil (RFB)
FAIXAS_IRPF_ANUAL = [
    {"limite": 27110.40, "aliquota": 0.000, "parcela_deduzir": 0.00},
    {"limite": 33919.80, "aliquota": 0.075, "parcela_deduzir": 2033.28},
    {"limite": 45012.60, "aliquota": 0.150, "parcela_deduzir": 4577.27},
    {"limite": 55976.16, "aliquota": 0.225, "parcela_deduzir": 7953.21},
    {"limite": float("inf"), "aliquota": 0.275, "parcela_deduzir": 10752.02},
]

DEDUCAO_ANUAL_POR_DEPENDENTE = 2275.08
LIMITE_ANUAL_INSTRUCAO = 3561.50
TETO_DESCONTO_SIMPLIFICADO = 16754.34
PERC_DESCONTO_SIMPLIFICADO = 0.20
TETO_PERC_PGBL = 0.12


@dataclass
class DeclaracaoInput:
    rendimentos_tributaveis: float = 0.0
    previdencia_oficial_inss: float = 0.0
    irrf_retido: float = 0.0
    num_dependentes: int = 0
    despesas_medicas: float = 0.0
    despesas_instrucao: float = 0.0
    previdencia_pgbl: float = 0.0
    pensao_alimenticia: float = 0.0
    outras_deducoes: float = 0.0
    rendimentos_isentos: float = 0.0
    rendimentos_exclusivos: float = 0.0


def calcular_imposto_pela_tabela(base_calculo: float) -> float:
    if base_calculo <= 0:
        return 0.0
    for faixa in FAIXAS_IRPF_ANUAL:
        if base_calculo <= faixa["limite"]:
            imposto = (base_calculo * faixa["aliquota"]) - faixa["parcela_deduzir"]
            return max(0.0, imposto)
    return 0.0


def apurar_declaracao(dados: DeclaracaoInput) -> Dict[str, Any]:
    # 1. Deduções Legais (Modelo Completo)
    deducao_dependentes = dados.num_dependentes * DEDUCAO_ANUAL_POR_DEPENDENTE
    deducao_educacao = min(dados.despesas_instrucao, LIMITE_ANUAL_INSTRUCAO * max(1, dados.num_dependentes + 1))
    teto_pgbl_permitido = dados.rendimentos_tributaveis * TETO_PERC_PGBL
    deducao_pgbl = min(dados.previdencia_pgbl, teto_pgbl_permitido)
    deducao_saude = dados.despesas_medicas  # Integralmente dedutível

    total_deducoes_legais = (
        dados.previdencia_oficial_inss
        + deducao_dependentes
        + deducao_educacao
        + deducao_saude
        + deducao_pgbl
        + dados.pensao_alimenticia
        + dados.outras_deducoes
    )

    base_completa = max(0.0, dados.rendimentos_tributaveis - total_deducoes_legais)
    imposto_devido_completo = calcular_imposto_pela_tabela(base_completa)
    saldo_completo = dados.irrf_retido - imposto_devido_completo
    aliq_efetiva_completa = (imposto_devido_completo / dados.rendimentos_tributaveis * 100) if dados.rendimentos_tributaveis > 0 else 0.0

    # 2. Desconto Simplificado
    desconto_simplificado = min(dados.rendimentos_tributaveis * PERC_DESCONTO_SIMPLIFICADO, TETO_DESCONTO_SIMPLIFICADO)
    base_simplificada = max(0.0, dados.rendimentos_tributaveis - desconto_simplificado)
    imposto_devido_simplificado = calcular_imposto_pela_tabela(base_simplificada)
    saldo_simplificado = dados.irrf_retido - imposto_devido_simplificado
    aliq_efetiva_simplificada = (imposto_devido_simplificado / dados.rendimentos_tributaveis * 100) if dados.rendimentos_tributaveis > 0 else 0.0

    # 3. Decisão / Recomendação
    if saldo_completo > saldo_simplificado:
        melhor_opcao = "Deducoes Legais (Modelo Completo)"
        diferenca_vantagem = saldo_completo - saldo_simplificado
    else:
        melhor_opcao = "Desconto Simplificado (Modelo Simplificado)"
        diferenca_vantagem = saldo_simplificado - saldo_completo

    return {
        "entradas": asdict(dados),
        "modelo_completo": {
            "total_deducoes": round(total_deducoes_legais, 2),
            "base_calculo": round(base_completa, 2),
            "imposto_devido": round(imposto_devido_completo, 2),
            "irrf_retido": round(dados.irrf_retido, 2),
            "saldo_final": round(saldo_completo, 2),
            "tipo_saldo": "A Restituir" if saldo_completo >= 0 else "A Pagar",
            "aliquota_efetiva_pct": round(aliq_efetiva_completa, 2),
            "detalhe_deducoes": {
                "inss": round(dados.previdencia_oficial_inss, 2),
                "dependentes": round(deducao_dependentes, 2),
                "saude": round(deducao_saude, 2),
                "educacao": round(deducao_educacao, 2),
                "pgbl": round(deducao_pgbl, 2),
                "pensao": round(dados.pensao_alimenticia, 2),
            },
        },
        "modelo_simplificado": {
            "desconto_simplificado": round(desconto_simplificado, 2),
            "base_calculo": round(base_simplificada, 2),
            "imposto_devido": round(imposto_devido_simplificado, 2),
            "irrf_retido": round(dados.irrf_retido, 2),
            "saldo_final": round(saldo_simplificado, 2),
            "tipo_saldo": "A Restituir" if saldo_simplificado >= 0 else "A Pagar",
            "aliquota_efetiva_pct": round(aliq_efetiva_simplificada, 2),
        },
        "recomendacao": {
            "melhor_modelo": melhor_opcao,
            "vantagem_financeira": round(diferenca_vantagem, 2),
        },
    }


def formatar_moeda(val: float) -> str:
    s = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def exibir_relatorio(resultado: Dict[str, Any]):
    com = resultado["modelo_completo"]
    sim = resultado["modelo_simplificado"]
    rec = resultado["recomendacao"]
    ent = resultado["entradas"]

    print("=" * 78)
    print("ORGANIZADOR E SIMULADOR DE IMPOSTO DE RENDA (IRPF)")
    print("Autor: Wendel Vieira | Base Normativa: RFB")
    print("=" * 78)
    print(f"Rendimentos Tributaveis Brutos : {formatar_moeda(ent['rendimentos_tributaveis'])}")
    print(f"Previdencia Oficial (INSS)     : {formatar_moeda(ent['previdencia_oficial_inss'])}")
    print(f"IRRF Retido na Fonte           : {formatar_moeda(ent['irrf_retido'])}")
    print("-" * 78)
    print(f"{'Item de Comparacao':<35} | {'Deducoes Legais':<18} | {'Simplificado':<18}")
    print("-" * 78)
    print(f"{'Deducoes / Desconto Padrao':<35} | {formatar_moeda(com['total_deducoes']):<18} | {formatar_moeda(sim['desconto_simplificado']):<18}")
    print(f"{'Base de Calculo do IRPF':<35} | {formatar_moeda(com['base_calculo']):<18} | {formatar_moeda(sim['base_calculo']):<18}")
    print(f"{'Imposto Anual Devido':<35} | {formatar_moeda(com['imposto_devido']):<18} | {formatar_moeda(sim['imposto_devido']):<18}")
    aliq_c_str = f"{com['aliquota_efetiva_pct']} %"
    aliq_s_str = f"{sim['aliquota_efetiva_pct']} %"
    print(f"{'Aliquota Efetiva (%)':<35} | {aliq_c_str:<18} | {aliq_s_str:<18}")
    print(f"{'IRRF Ja Retido':<35} | {formatar_moeda(com['irrf_retido']):<18} | {formatar_moeda(sim['irrf_retido']):<18}")
    print("-" * 78)
    
    saldo_c_str = f"{com['tipo_saldo']}: {formatar_moeda(abs(com['saldo_final']))}"
    saldo_s_str = f"{sim['tipo_saldo']}: {formatar_moeda(abs(sim['saldo_final']))}"
    print(f"{'SALDO FINAL APURADO':<35} | {saldo_c_str:<18} | {saldo_s_str:<18}")
    print("=" * 78)
    print(f"RECOMENDACAO: {rec['melhor_modelo']}")
    print(f"Vantagem Economica Estimada: {formatar_moeda(rec['vantagem_financeira'])}")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(description="Simulador e Apurador de IRPF - Wendel Vieira")
    parser.add_argument("--rendimentos", type=float, default=169000.0, help="Total rendimentos tributáveis (R$)")
    parser.add_argument("--inss", type=float, default=15160.0, help="INSS retido anual (R$)")
    parser.add_argument("--irrf", type=float, default=18150.0, help="IRRF retido na fonte anual (R$)")
    parser.add_argument("--dependentes", type=int, default=1, help="Quantidade de dependentes")
    parser.add_argument("--saude", type=float, default=6050.0, help="Despesas médicas comprovadas (R$)")
    parser.add_argument("--educacao", type=float, default=14500.0, help="Despesas de instrução (R$)")
    parser.add_argument("--pgbl", type=float, default=9500.0, help="Aportes em PGBL (R$)")
    parser.add_argument("--pensao", type=float, default=0.0, help="Pensão alimentícia judicial (R$)")
    parser.add_argument("--json", action="store_true", help="Retorna saída estruturada em JSON")
    parser.add_argument("--export-csv", type=str, default="", help="Exporta resultado para arquivo CSV")

    args = parser.parse_args()

    dados = DeclaracaoInput(
        rendimentos_tributaveis=args.rendimentos,
        previdencia_oficial_inss=args.inss,
        irrf_retido=args.irrf,
        num_dependentes=args.dependentes,
        despesas_medicas=args.saude,
        despesas_instrucao=args.educacao,
        previdencia_pgbl=args.pgbl,
        pensao_alimenticia=args.pensao,
    )

    resultado = apurar_declaracao(dados)

    if args.json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        return

    exibir_relatorio(resultado)

    if args.export_csv:
        with open(args.export_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Métrica", "Modelo Completo", "Modelo Simplificado"])
            writer.writerow(["Rendimentos Tributáveis", dados.rendimentos_tributaveis, dados.rendimentos_tributaveis])
            writer.writerow(["Deduções / Desconto", resultado["modelo_completo"]["total_deducoes"], resultado["modelo_simplificado"]["desconto_simplificado"]])
            writer.writerow(["Base de Cálculo", resultado["modelo_completo"]["base_calculo"], resultado["modelo_simplificado"]["base_calculo"]])
            writer.writerow(["Imposto Devido", resultado["modelo_completo"]["imposto_devido"], resultado["modelo_simplificado"]["imposto_devido"]])
            writer.writerow(["Alíquota Efetiva (%)", resultado["modelo_completo"]["aliquota_efetiva_pct"], resultado["modelo_simplificado"]["aliquota_efetiva_pct"]])
            writer.writerow(["IRRF Retido", resultado["modelo_completo"]["irrf_retido"], resultado["modelo_simplificado"]["irrf_retido"]])
            writer.writerow(["Saldo Final", resultado["modelo_completo"]["saldo_final"], resultado["modelo_simplificado"]["saldo_final"]])
        print(f"\n[OK] Relatório exportado com sucesso para: {args.export_csv}")


if __name__ == "__main__":
    main()
