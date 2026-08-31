"""
build_site_nova.py — Orquestrador delega a implementacao da landing SentinelaEdge
para a Nova (Frontend) do squad, conforme blueprint_R00.

Uso: uv run python build_site_nova.py
Saida: sites/sentinelaedge/index.html
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "agents"))
from agent_runner import load_agent, call_agent  # noqa: E402

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "sites" / "sentinelaedge"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TASK = """\
Implemente a LANDING PAGE do produto **SentinelaEdge** como UM UNICO arquivo `index.html`
AUTOCONTIDO (Tailwind CSS via CDN <script src="https://cdn.tailwindcss.com"></script>,
fontes Google Inter, JS vanilla inline). Sem build, abre direto no navegador.

PRODUTO: servidores de vigilancia de borda feitos de notebooks reaproveitados.
Specs: 4GB RAM, 1TB armazenamento, Debian Server, conecta camera IP/analogica/DVR/NAS,
acesso remoto, reconhecimento facial por IA, bateria 6h (grava na queda de energia).

DESIGN SYSTEM (seguir exatamente):
- Tema DARK, moderno, tech, confiavel.
- Paleta: fundo #0A1628; superficies #1E293B; primaria/destaque ciano #00D9FF;
  acento eco verde #00FF88 (so em badges de sustentabilidade); texto #FFFFFF/#94A3B8.
- Tipografia: Inter (headings bold). Specs tecnicas em fonte monospace.
- Microinteracoes: hover nos botoes/cards, fade-in/slide-up ao rolar (IntersectionObserver).

SECOES OBRIGATORIAS (nesta ordem):
1. Navbar fixa com logo "SentinelaEdge", links ancora e botao CTA "Solicitar Orcamento".
2. HERO: headline forte (destaque autonomia 6h + IA), subheadline com specs, 2 CTAs, mockup/visual do servidor.
3. BENEFICIOS: 4 cards (Economia, Autonomia 6h, IA Reconhecimento Facial, Sustentabilidade) com icones SVG inline.
4. ESPECIFICACOES: tabela comparativa SentinelaEdge vs Sistema Tradicional + chips de compatibilidade (IP, Analogica, DVR, NAS).
5. CASOS DE USO: 3 cards (Comercio, Condominio, Residencia).
6. PLANOS: 3 cards de preco (ex: Essencial / Profissional[destacado] / Empresarial) com botao CTA cada.
7. PROVA SOCIAL: 3 depoimentos com nome/cargo.
8. FAQ: accordion com 6 perguntas (confiabilidade, garantia, instalacao, queda de energia, acesso remoto, privacidade).
9. CTA FINAL + formulario de lead (nome, email, telefone, tipo de negocio) — validacao basica JS, sem backend (mostra alerta de sucesso).
10. Footer + botao WhatsApp flutuante fixo no canto inferior direito.

REGRAS DE COPY: portugues BR. NUNCA usar "barato", "usado" ou "reciclado" — usar "reaproveitado",
"sustentavel", "custo-beneficio". Tom profissional, confiante, sem jargao excessivo.

RESPONDA APENAS com o conteudo COMPLETO do arquivo index.html (comecando em <!DOCTYPE html>).
SEM explicacoes, SEM comentarios fora do HTML, SEM cercas markdown. O arquivo deve ser valido e completo.
"""


def strip_fences(text: str) -> str:
    text = text.strip()
    # remove cercas ```html ... ```
    m = re.search(r"```(?:html)?\s*(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    # garante que comeca no doctype
    idx = text.lower().find("<!doctype")
    if idx > 0:
        text = text[idx:]
    return text.strip()


def main() -> None:
    nova = load_agent("nova")
    print(f"Delegando para Nova ({nova.get('model')}) — Tier {nova.get('tier')} {nova.get('specialty')}")
    res = call_agent(nova, TASK, max_tokens=16000)
    if not res["success"]:
        raise SystemExit(f"ERRO Nova: {res['error']}")

    html = strip_fences(res["content"])
    out = OUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")

    print(f"finish_reason : {res['finish_reason']}")
    print(f"tokens        : {res['prompt_tokens']} in / {res['completion_tokens']} out")
    print(f"bytes salvos  : {len(html)}")
    print(f"arquivo       : {out}")
    print(f"fecha </html> : {'</html>' in html.lower()}")


if __name__ == "__main__":
    main()
