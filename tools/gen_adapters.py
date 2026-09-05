#!/usr/bin/env python3
"""
tools/gen_adapters.py -- Propagacao da governanca para os adaptadores de IDE/CLI.

Topologia (a mesma de agents/sync_pool.py, aplicada a governanca):

  docs/AI_CHARTER.md    FONTE. Bloco entre <!-- PISO:INICIO --> e <!-- PISO:FIM -->
                        e o nucleo inegociavel, copiado inteiro para cada adaptador.

  CLAUDE.md             ADAPTADORES. Gerados, descartaveis. Ferramenta morreu?
  .clinerules           Some a linha do manifest. Ferramenta nova? Adiciona uma.
  .cursorrules
  AGENTS.md

Comandos:
  python tools/gen_adapters.py                    # --sync (padrao): regera todos
  python tools/gen_adapters.py --check            # falha se algum divergiu (pre-commit)
  python tools/gen_adapters.py --promote CLAUDE.md  # sobe o PISO editado no adaptador
                                                    # para o charter e regera todos

A geracao e de mao unica (charter -> adaptadores). O caminho de volta e o
--promote, explicito, porque duas ferramentas escrevendo no mesmo nucleo sem
passo declarado tornam impossivel saber qual arquivo e a verdade em repouso.
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
MANIFEST_PATH: Path = ROOT_DIR / "rdf.manifest.json"

PISO_INICIO: str = "<!-- PISO:INICIO -->"
PISO_FIM: str = "<!-- PISO:FIM -->"


# ---------------------------------------------------------------------------
# Tipos (ADR-005: tipos antes da logica)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Adaptador:
    """Um arquivo de instrucao gerado para uma ferramenta especifica."""

    arquivo: str
    ferramenta: str
    hooks_pre_execucao: bool
    nota: str | None = None

    @property
    def caminho(self) -> Path:
        return ROOT_DIR / self.arquivo


@dataclass(frozen=True)
class Nucleo:
    """Os documentos que formam a verdade, apontados por todo adaptador."""

    charter: str
    kit: str
    playbooks: str
    blueprint: str
    decisoes: list[str]
    handover: list[str]


@dataclass(frozen=True)
class Manifest:
    versao: int
    produto: str
    nucleo: Nucleo
    adaptadores: list[Adaptador]


class GovernancaError(RuntimeError):
    """Falha estrutural: manifest, charter ou marcadores em estado invalido."""


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


def ler(path: Path) -> str:
    """Le em UTF-8 normalizando para LF, para o diff nao acusar fim de linha."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def escrever(path: Path, conteudo: str) -> None:
    """Escreve sempre em LF: o repo e compartilhado entre Windows e WSL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8", newline="\n")


def carregar_manifest() -> Manifest:
    if not MANIFEST_PATH.exists():
        raise GovernancaError(f"manifest ausente: {MANIFEST_PATH}")
    dados = json.loads(ler(MANIFEST_PATH))
    return Manifest(
        versao=int(dados["versao"]),
        produto=str(dados["produto"]),
        nucleo=Nucleo(**dados["nucleo"]),
        adaptadores=[Adaptador(**a) for a in dados["adaptadores"]],
    )


def extrair_piso(texto: str, origem: str) -> str:
    """Devolve o conteudo entre os marcadores PISO, sem os marcadores."""
    if PISO_INICIO not in texto or PISO_FIM not in texto:
        raise GovernancaError(
            f"{origem}: marcadores {PISO_INICIO} / {PISO_FIM} nao encontrados"
        )
    inicio = texto.index(PISO_INICIO) + len(PISO_INICIO)
    fim = texto.index(PISO_FIM)
    if fim < inicio:
        raise GovernancaError(f"{origem}: PISO:FIM aparece antes de PISO:INICIO")
    return texto[inicio:fim].strip("\n")


def substituir_piso(texto: str, piso: str, origem: str) -> str:
    """Troca o conteudo entre os marcadores, preservando o resto do arquivo."""
    if PISO_INICIO not in texto or PISO_FIM not in texto:
        raise GovernancaError(f"{origem}: marcadores PISO nao encontrados")
    antes = texto[: texto.index(PISO_INICIO) + len(PISO_INICIO)]
    depois = texto[texto.index(PISO_FIM) :]
    return f"{antes}\n{piso}\n{depois}"


# ---------------------------------------------------------------------------
# Renderizacao -- deterministica: sem data, sem hash volatil, senao --check
# acusaria drift a cada execucao.
# ---------------------------------------------------------------------------


def renderizar(adaptador: Adaptador, piso: str, manifest: Manifest) -> str:
    n = manifest.nucleo
    rede = (
        "Esta ferramenta tem hooks de pre-execucao; eles complementam o pre-commit."
        if adaptador.hooks_pre_execucao
        else "Esta ferramenta nao tem hooks de pre-execucao conhecidos: a rede e o `hooks/pre-commit`."
    )
    decisoes = "<br>".join(f"`{d}`" for d in n.decisoes)
    handover = " ou ".join(f"`{h}`" for h in n.handover)

    linhas: list[str] = [
        "<!-- =========================================================",
        f"     GERADO por tools/gen_adapters.py -- ferramenta: {adaptador.ferramenta}",
        f"     Fonte: {n.charter} (bloco PISO). NAO EDITE ESTE ARQUIVO A MAO.",
        f"     Editou aqui? python tools/gen_adapters.py --promote {adaptador.arquivo}",
        "     ========================================================= -->",
        "",
        f"# Governanca do {manifest.produto}",
        "",
        PISO_INICIO,
        piso,
        PISO_FIM,
        "",
        "---",
        "",
        "## Onde esta o resto (aponte, nao cole)",
        "",
        "| O que | Onde |",
        "|---|---|",
        f"| Charter completo -- squad, operacao, playbooks, congelados | `{n.charter}` |",
        f"| Kit de governanca de projeto | `{n.kit}` |",
        f"| Playbooks (leia o arquivo antes de executar) | `{n.playbooks}` |",
        f"| Tese do produto | `{n.blueprint}` |",
        f"| Decisoes vigentes (nao re-litigar) | {decisoes} |",
        f"| Handover -- use o formato da sua ferramenta | {handover} |",
        "",
        f"> {rede}",
        "",
    ]
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------


def sync(manifest: Manifest) -> int:
    charter = ROOT_DIR / manifest.nucleo.charter
    piso = extrair_piso(ler(charter), manifest.nucleo.charter)
    escritos = 0
    for adaptador in manifest.adaptadores:
        novo = renderizar(adaptador, piso, manifest)
        atual = ler(adaptador.caminho) if adaptador.caminho.exists() else None
        if atual == novo:
            print(f"  [ok]      {adaptador.arquivo}")
            continue
        escrever(adaptador.caminho, novo)
        print(f"  [gerado]  {adaptador.arquivo}  ({adaptador.ferramenta})")
        escritos += 1
    print(f"\n{escritos} adaptador(es) atualizado(s), {len(manifest.adaptadores)} no total.")
    return 0


def check(manifest: Manifest) -> int:
    charter = ROOT_DIR / manifest.nucleo.charter
    piso = extrair_piso(ler(charter), manifest.nucleo.charter)
    divergentes: list[Adaptador] = []
    for adaptador in manifest.adaptadores:
        if not adaptador.caminho.exists():
            divergentes.append(adaptador)
            continue
        if ler(adaptador.caminho) != renderizar(adaptador, piso, manifest):
            divergentes.append(adaptador)

    if not divergentes:
        print(f"governanca: {len(manifest.adaptadores)} adaptador(es) em dia.")
        return 0

    print("GOVERNANCA FORA DE SINCRONIA -- adaptador editado a mao ou desatualizado:\n")
    for a in divergentes:
        estado = "ausente" if not a.caminho.exists() else "divergente"
        print(f"  - {a.arquivo}  ({estado})")
    print(
        "\nA fonte e o charter, nao o adaptador. Escolha:\n"
        f"  manter a edicao   -> python tools/gen_adapters.py --promote <arquivo>\n"
        f"  descartar a edicao-> python tools/gen_adapters.py --sync"
    )
    return 1


def promote(manifest: Manifest, arquivo: str) -> int:
    alvo = next((a for a in manifest.adaptadores if a.arquivo == arquivo), None)
    if alvo is None:
        conhecidos = ", ".join(a.arquivo for a in manifest.adaptadores)
        print(f"'{arquivo}' nao e um adaptador. Conhecidos: {conhecidos}")
        return 1
    if not alvo.caminho.exists():
        print(f"{arquivo} nao existe no disco.")
        return 1

    piso_novo = extrair_piso(ler(alvo.caminho), arquivo)
    charter_path = ROOT_DIR / manifest.nucleo.charter
    charter_texto = ler(charter_path)
    piso_atual = extrair_piso(charter_texto, manifest.nucleo.charter)

    if piso_novo == piso_atual:
        print(f"{arquivo}: PISO identico ao charter — nada a promover.")
        print("(Edicoes fora do bloco PISO nao sobem: elas pertencem ao charter.)")
        return sync(manifest)

    escrever(charter_path, substituir_piso(charter_texto, piso_novo, manifest.nucleo.charter))
    print(f"PISO promovido de {arquivo} -> {manifest.nucleo.charter}\n")
    print("ATENCAO: so o bloco PISO sobe. Qualquer edicao que voce tenha feito")
    print("fora dele neste adaptador foi descartada na regeracao abaixo.\n")
    return sync(manifest)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Propaga docs/AI_CHARTER.md para os adaptadores de IDE/CLI."
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--sync", action="store_true", help="regera todos os adaptadores (padrao)")
    grupo.add_argument("--check", action="store_true", help="falha se algum divergiu")
    grupo.add_argument("--promote", metavar="ARQUIVO", help="sobe o PISO do adaptador para o charter")
    args = parser.parse_args()

    try:
        manifest = carregar_manifest()
        if args.check:
            return check(manifest)
        if args.promote:
            return promote(manifest, args.promote)
        return sync(manifest)
    except GovernancaError as erro:
        print(f"ERRO DE GOVERNANCA: {erro}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
