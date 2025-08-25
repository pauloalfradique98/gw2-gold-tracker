import csv
import os
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation, getcontext

# Precisão segura para 2 casas decimais
getcontext().prec = 28

# Diretório onde o script está localizado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "gold.csv")

def log_gold(amount):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([now, amount])


MENU = """
=-=-=-=-=-=-=-=-= GW2 Gold Tracker =-=-=-=-=-=-=-=-=
1) Registrar GANHO (+)
2) Registrar GASTO (-)
3) Listar movimentações de HOJE
4) Resumo: hoje / 7 dias / mês atual
5) Desfazer última movimentação
Q) Sair
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
Escolha uma opção: """

def ensure_data_file():
    """Cria o CSV com cabeçalho se não existir."""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "time", "type", "category", "amount", "notes"])

def parse_amount(text: str) -> Decimal:
    """
    Converte string para Decimal.
    Aceita vírgula ou ponto. Ex.: '12,5' -> 12.50
    """
    try:
        normalized = text.strip().replace(",", ".")
        value = Decimal(normalized)
        # Garante 2 casas
        return value.quantize(Decimal("0.01"))
    except (InvalidOperation, AttributeError):
        raise ValueError("Valor inválido. Use números, ex.: 10.5 ou 10,5")

def fmt_amount(value: Decimal) -> str:
    """Formata para exibição (2 casas + 'g')."""
    return f"{value.quantize(Decimal('0.01'))}g"

def add_transaction(kind: str):
    """Adiciona uma linha no CSV: kind = 'gain' ou 'spend'."""
    assert kind in ("gain", "spend")
    ensure_data_file()
    print("\n— Adicionar movimentação —")
    raw_amount = input("Valor (em gold, ex.: 12.5 ou 12,5): ").strip()
    try:
        amount = parse_amount(raw_amount)
    except ValueError as e:
        print(f"Erro: {e}\n")
        return

    category = input("Categoria (ex.: Fractals, TP, Dailies, Crafting): ").strip() or "Other"
    notes = input("Observações (opcional): ").strip()

    now = datetime.now()
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([now.date().isoformat(),
                         now.strftime("%H:%M"),
                         kind,
                         category,
                         str(amount),  # guarda como string Decimal
                         notes])

    sinal = "+" if kind == "gain" else "-"
    print(f"OK! Registrado {sinal}{fmt_amount(amount)} em '{category}'.\n")

def read_all_rows():
    """Lê todas as movimentações como dicts."""
    ensure_data_file()
    rows = []
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def list_today():
    """Lista as movimentações do dia atual."""
    rows = read_all_rows()
    today = date.today().isoformat()
    today_rows = [r for r in rows if r["date"] == today]

    if not today_rows:
        print("\n— Hoje —")
        print("Nenhuma movimentação hoje.\n")
        return

    print("\n— Hoje —")
    gain_total = Decimal("0")
    spend_total = Decimal("0")
    for i, r in enumerate(today_rows, start=1):
        amt = Decimal(r["amount"])
        sign = "+" if r["type"] == "gain" else "-"
        if r["type"] == "gain":
            gain_total += amt
        else:
            spend_total += amt
        print(f"{i:02d}. {r['time']} {sign}{fmt_amount(amt)}  [{r['category']}]  {r['notes']}")
    net = gain_total - spend_total
    print(f"\nGanhos: {fmt_amount(gain_total)} | Gastos: {fmt_amount(spend_total)} | "
          f"Saldo do dia: {fmt_amount(net)}\n")

def summary():
    """Mostra resumo: hoje, últimos 7 dias e mês atual."""
    rows = read_all_rows()
    if not rows:
        print("\nSem dados ainda. Registre algo primeiro.\n")
        return

    def period_sum(start_date: date, end_date: date):
        gains = Decimal("0")
        spends = Decimal("0")
        for r in rows:
            d = date.fromisoformat(r["date"])
            if start_date <= d <= end_date:
                amt = Decimal(r["amount"])
                if r["type"] == "gain":
                    gains += amt
                else:
                    spends += amt
        return gains, spends, gains - spends

    today = date.today()
    # Hoje
    g1, s1, n1 = period_sum(today, today)
    # Últimos 7 dias (hoje inclusive)
    g7, s7, n7 = period_sum(today - timedelta(days=6), today)
    # Mês atual
    month_start = today.replace(day=1)
    gM, sM, nM = period_sum(month_start, today)

    print("\n— Resumo —")
    print(f"Hoje........... Ganhos {fmt_amount(g1)} | Gastos {fmt_amount(s1)} | Saldo {fmt_amount(n1)}")
    print(f"Últimos 7 dias. Ganhos {fmt_amount(g7)} | Gastos {fmt_amount(s7)} | Saldo {fmt_amount(n7)}")
    print(f"Mês atual...... Ganhos {fmt_amount(gM)} | Gastos {fmt_amount(sM)} | Saldo {fmt_amount(nM)}\n")

def undo_last():
    """Remove a última linha do CSV (última movimentação)."""
    rows = read_all_rows()
    if not rows:
        print("\nNada para desfazer.\n")
        return
    last = rows[-1]
    print("\nÚltima movimentação:")
    sign = "+" if last["type"] == "gain" else "-"
    print(f"{last['date']} {last['time']} {sign}{fmt_amount(Decimal(last['amount']))} "
          f"[{last['category']}] {last['notes']}")
    confirm = input("Tem certeza que deseja remover? (s/N): ").strip().lower()
    if confirm != "s":
        print("Cancelado.\n")
        return
    # Reescreve o arquivo sem a última linha
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "time", "type", "category", "amount", "notes"])
        for r in rows[:-1]:
            writer.writerow([r["date"], r["time"], r["type"], r["category"], r["amount"], r["notes"]])
    print("Última movimentação removida.\n")

def main():
    ensure_data_file()
    while True:
        choice = input(MENU).strip().lower()
        if choice == "1":
            add_transaction("gain")
        elif choice == "2":
            add_transaction("spend")
        elif choice == "3":
            list_today()
        elif choice == "4":
            summary()
        elif choice == "5":
            undo_last()
        elif choice in ("q", "quit", "sair"):
            print("Até mais! 🐉")
            break
        else:
            print("Opção inválida.\n")

if __name__ == "__main__":
    main()
