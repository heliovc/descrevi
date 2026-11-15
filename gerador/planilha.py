"""Planilha (xlsx) e CSV do Anúncio Pronto — um arquivo por pedido, várias abas/linhas."""
from __future__ import annotations
import csv
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from gerador.checagem import montar_descricao_corrida, ML_TITULO, SHOPEE_TITULO, listar_confirmacoes

FOREST = "1A4A3C"
SOFT = "E4EFE9"


def _cab(ws, titulos):
    fill = PatternFill("solid", fgColor=FOREST)
    font = Font(name="Calibri", bold=True, color="FFFFFF")
    for i, t in enumerate(titulos, 1):
        c = ws.cell(1, i, t)
        c.fill = fill
        c.font = font
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(titulos))}1"


def _ajusta(ws, larguras):
    for i, w in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    thin = Border(left=Side(style="thin", color="D5CDBE"), right=Side(style="thin", color="D5CDBE"),
                  top=Side(style="thin", color="D5CDBE"), bottom=Side(style="thin", color="D5CDBE"))
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.font = Font(name="Calibri", size=11)
            cell.border = thin


def linhas_planas(itens_gerados: list[dict]) -> list[list]:
    rows = []
    for i, bloco in enumerate(itens_gerados, 1):
        item, anuncio = bloco["item"], bloco["anuncio"]
        nome = item.get("nome_produto") or f"Produto {i}"
        plat = item.get("plataforma") or "ambos"
        link = item.get("link_referencia") or ""
        confs = list(anuncio.get("confirmacoes") or listar_confirmacoes(anuncio))
        ja = set(s.lower() for s in confs)
        for p in anuncio.get("pendencias") or []:
            txt = str(p).strip()
            if txt and txt.lower() not in ja:
                confs.append(txt)
                ja.add(txt.lower())
        if confs:
            resumo = " · ".join(c if c.lower().startswith("[confirmar:") else f"[confirmar: {c}]" for c in confs)
            rows.append([i, nome, plat, "Itens para você confirmar", resumo, len(confs), "", "Complete ou confirme antes de publicar", link])
            for c in confs:
                rotulo = c if c.lower().startswith("[confirmar:") else f"[confirmar: {c}]"
                rows.append([i, nome, plat, "Confirmar", rotulo, "", "", "", link])
        if plat in ("ml", "ambos"):
            for j, t in enumerate(anuncio.get("titulos_ml") or [], 1):
                txt = (t.get("texto") or "").strip()
                rows.append([i, nome, "Mercado Livre", f"Título opção {j}", txt, len(txt), ML_TITULO, t.get("enfoque") or "", link])
        if plat in ("shopee", "ambos"):
            txt = ((anuncio.get("titulo_shopee") or {}).get("texto") or "").strip()
            rows.append([i, nome, "Shopee", "Título", txt, len(txt), SHOPEE_TITULO, (anuncio.get("titulo_shopee") or {}).get("enfoque") or "", link])
        desc = montar_descricao_corrida(anuncio.get("descricao") or {})
        rows.append([i, nome, plat, "Descrição", desc, len(desc), "", "", link])
        for par in anuncio.get("ficha_tecnica") or []:
            rows.append([i, nome, plat, f"Ficha · {par.get('caracteristica') or ''}", par.get("valor") or "", "", "", "", link])
        for j, p in enumerate(anuncio.get("perguntas") or [], 1):
            rows.append([i, nome, plat, f"Pergunta {j}", p.get("pergunta") or "", "", "", "", link])
            rows.append([i, nome, plat, f"Resposta {j}", p.get("resposta") or "", "", "", "", link])
        for f in sorted(anuncio.get("roteiro_fotos") or [], key=lambda x: x.get("ordem") or 0):
            rows.append([i, nome, plat, f"Foto {f.get('ordem')}", f.get("o_que_mostrar") or "", "", "", f.get("dica") or "", link])
    return rows


CAB = ["#", "Produto", "Plataforma", "Tipo", "Texto", "Caracteres", "Limite", "Nota", "Link de referência (não acessado)"]


def escrever_xlsx(itens_gerados: list[dict], destino: Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Anuncio Pronto"
    _cab(ws, CAB)
    for r, row in enumerate(linhas_planas(itens_gerados), 2):
        for c, val in enumerate(row, 1):
            ws.cell(r, c, val)
    _ajusta(ws, [6, 28, 18, 22, 70, 12, 10, 28, 40])
    # uma aba por produto, mais confortável para colar
    for i, bloco in enumerate(itens_gerados, 1):
        nome = (bloco["item"].get("nome_produto") or f"Produto {i}")[:28]
        w = wb.create_sheet(f"{i}. {nome}")
        _cab(w, ["Campo", "Texto", "Caracteres"])
        recortes = [r for r in linhas_planas([bloco])]
        for r, row in enumerate(recortes, 2):
            w.cell(r, 1, f"{row[2]} · {row[3]}")
            w.cell(r, 2, row[4])
            w.cell(r, 3, row[5] if row[5] != "" else None)
        _ajusta(w, [28, 80, 12])
    wb.save(destino)
    return destino


def escrever_csv(itens_gerados: list[dict], destino: Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CAB)
        w.writerows(linhas_planas(itens_gerados))
    return destino
