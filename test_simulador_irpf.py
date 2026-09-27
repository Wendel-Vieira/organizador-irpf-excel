"""
Testes Unitários do Simulador de IRPF
Autor: Wendel Vieira
"""

import unittest
from simulador_irpf import (
    DeclaracaoInput,
    apurar_declaracao,
    calcular_imposto_pela_tabela,
    DEDUCAO_ANUAL_POR_DEPENDENTE,
    TETO_DESCONTO_SIMPLIFICADO,
)


class TestSimuladorIRPF(unittest.TestCase):

    def test_isencao_total(self):
        """Rendimentos dentro da faixa de isenção anual não pagam imposto."""
        imposto = calcular_imposto_pela_tabela(25000.0)
        self.assertEqual(imposto, 0.0)

    def test_faixa_dois(self):
        """Teste de cálculo na 2ª faixa (7,5%)."""
        base = 30000.0
        esperado = (30000.0 * 0.075) - 2033.28
        imposto = calcular_imposto_pela_tabela(base)
        self.assertAlmostEqual(imposto, esperado, places=2)

    def test_teto_desconto_simplificado(self):
        """O desconto simplificado não deve ultrapassar o limite legal de R$ 16.754,34."""
        dados = DeclaracaoInput(rendimentos_tributaveis=200000.0)
        res = apurar_declaracao(dados)
        self.assertEqual(
            res["modelo_simplificado"]["desconto_simplificado"],
            TETO_DESCONTO_SIMPLIFICADO
        )

    def test_deducao_dependentes(self):
        """A dedução por dependente deve ser multiplicada pelo número de dependentes."""
        dados = DeclaracaoInput(rendimentos_tributaveis=100000.0, num_dependentes=2)
        res = apurar_declaracao(dados)
        self.assertEqual(
            res["modelo_completo"]["detalhe_deducoes"]["dependentes"],
            round(2 * DEDUCAO_ANUAL_POR_DEPENDENTE, 2)
        )

    def test_recomendacao_completa_quando_muitas_deducoes(self):
        """Com altas despesas médicas e dependentes, o modelo completo deve ser recomendado."""
        dados = DeclaracaoInput(
            rendimentos_tributaveis=120000.0,
            previdencia_oficial_inss=10000.0,
            num_dependentes=2,
            despesas_medicas=25000.0,
            irrf_retido=15000.0
        )
        res = apurar_declaracao(dados)
        self.assertEqual(
            res["recomendacao"]["melhor_modelo"],
            "Deducoes Legais (Modelo Completo)"
        )

    def test_recomendacao_simplificado_quando_poucas_deducoes(self):
        """Sem despesas dedutíveis relevantes, o modelo simplificado deve ser recomendado."""
        dados = DeclaracaoInput(
            rendimentos_tributaveis=80000.0,
            previdencia_oficial_inss=2000.0,
            num_dependentes=0,
            despesas_medicas=0.0,
            irrf_retido=5000.0
        )
        res = apurar_declaracao(dados)
        self.assertEqual(
            res["recomendacao"]["melhor_modelo"],
            "Desconto Simplificado (Modelo Simplificado)"
        )


if __name__ == "__main__":
    unittest.main()
