# libro_diario/ui.py
import argparse
from datetime import date
from .storage import JsonStorage
from .services import Entry, add_entry, list_entries

def _read_bank_csv_row(path: str, idx_one_based: int):
    """
    Lee el CSV bancario (delimitador ';') y devuelve un dict con los campos de la fila indicada (1-based).
    El CSV de ejemplo incluye una primera columna vacía y una cabecera con el texto 'Cantidades expresadas en euros'.
    Normalizamos para quedarnos con las 5 columnas útiles: Fecha, Fecha valor, Concepto, Importe, Saldo Posterior.
    """
    import csv
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=';')
        try:
            header = next(reader, None)
        except StopIteration:
            raise ValueError("CSV vacío")
        if header is None:
            raise ValueError("CSV vacío")
        # Normaliza las cabeceras para quedarnos con las 5 últimas columnas
        headers = header[-5:]
        # Recolecta filas no vacías (ignoramos la primera columna vacía cuando exista)
        for r in reader:
            if not r:
                continue
            # Tomamos las 5 últimas columnas para casar con headers
            data = r[-5:]
            if len(data) != 5:
                # Filas corruptas o en blanco
                continue
            rows.append(dict(zip(headers, data)))
    # Soportar índice 1-based (más natural para el usuario)
    real_index = idx_one_based - 1
    if real_index < 0 or real_index >= len(rows):
        raise IndexError(f"Índice fuera de rango: {idx_one_based}. Total filas: {len(rows)}")
    return rows[real_index]

def _iter_bank_csv_rows(path: str):
    """
    Itera todas las filas útiles del CSV bancario y devuelve una lista de dicts
    con las 5 columnas: Fecha, Fecha valor, Concepto, Importe, Saldo Posterior.
    """
    import csv
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader, None)
        if not header:
            return rows
        headers = header[-5:]
        for r in reader:
            if not r:
                continue
            data = r[-5:]
            if len(data) != 5:
                continue
            rows.append(dict(zip(headers, data)))
    return rows
def _parse_ddmmyyyy(s: str):
    from datetime import datetime
    # Acepta '04/09/2025' y también '4/9/2025'
    return datetime.strptime(s.strip(), "%d/%m/%Y").date()
def _parse_euro_amount(s: str) -> float:
    """
    Convierte una cantidad con coma decimal a float (p.ej. '-2,37' -> -2.37).
    Elimina separadores de miles con punto si aparecen.
    """
    s = s.strip().replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0

def _prompt_with_default(label: str, default: str) -> str:
    """
    Pide al usuario un valor en stdin mostrando un valor por defecto.
    Si el usuario pulsa Enter, devuelve el valor por defecto.
    """
    try:
        inp = input(f"{label} [{default}]: ").strip()
    except EOFError:
        # En entornos sin stdin, cae al valor por defecto
        return default
    return default if inp == "" else inp

def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="libro-diario", description="Libro Diario minimal")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Añadir asiento")
    p_add.add_argument("--fecha", default=date.today().isoformat(), help="YYYY-MM-DD (por defecto: hoy)")
    p_add.add_argument("--concepto", required=True)
    p_add.add_argument("--debe", type=float, default=0.0)
    p_add.add_argument("--haber", type=float, default=0.0)

    p_list = sub.add_parser("list", help="Listar asientos")
    p_list.add_argument("--raw", action="store_true", help="Imprimir objetos raw")

    p_bank = sub.add_parser("bank", help="Mostrar un movimiento del CSV bancario por índice (1-based)")
    p_bank.add_argument("--csv", required=True, help="Ruta al CSV exportado del banco")
    p_bank.add_argument("--id", type=int, required=True, help="Índice (1-based) del movimiento a mostrar")
    p_bank.add_argument("--raw", action="store_true", help="Imprimir el dict crudo del movimiento")

    p_bank_month = sub.add_parser("bank-month", help="Listar movimientos del CSV por mes (YYYY-MM)")
    p_bank_month.add_argument("--csv", required=True, help="Ruta al CSV exportado del banco")
    p_bank_month.add_argument("--month", required=True, help="Mes a filtrar en formato YYYY-MM (por ejemplo 2025-09)")
    p_bank_month.add_argument("--raw", action="store_true", help="Imprimir los dicts crudos")

    p_bank_add = sub.add_parser("bank-add", help="Crear un asiento en el JSON a partir de un movimiento del CSV por ID")
    p_bank_add.add_argument("--csv", required=True, help="Ruta al CSV exportado del banco")
    p_bank_add.add_argument("--id", type=int, required=True, help="Índice (1-based) del movimiento a usar")
    p_bank_add.add_argument("--fecha-col", choices=["Fecha", "Fecha valor"], default="Fecha", help="Columna de fecha a usar (por defecto: Fecha)")
    p_bank_add.add_argument("--no-interactive", action="store_true", help="Crear el asiento usando valores sugeridos sin preguntar")

    args = parser.parse_args(argv)
    storage = JsonStorage("data/libro_diario.json")

    if args.cmd == "add":
        e = Entry(
            fecha=date.fromisoformat(args.fecha),
            concepto=args.concepto,
            debe=args.debe,
            haber=args.haber,
        )
        add_entry(storage, e)
        print("Asiento guardado.")
    elif args.cmd == "list":
        entries = list_entries(storage)
        if args.raw:
            for e in entries:
                print(e)
            return
        total_debe = sum(e.debe for e in entries)
        total_haber = sum(e.haber for e in entries)
        for e in entries:
            print(f"{e.fecha.isoformat()} | {e.concepto:<30} | D:{e.debe:8.2f} | H:{e.haber:8.2f}")
        print("-" * 74)
        print(f"{'TOTAL':<35} D:{total_debe:8.2f} | H:{total_haber:8.2f} | Δ:{(total_debe-total_haber):8.2f}")
    elif args.cmd == "bank":
        try:
            row = _read_bank_csv_row(args.csv, args.id)
        except Exception as exc:
            print(f"Error leyendo CSV: {exc}")
            return
        if args.raw:
            print(row)
            return
        # Formateo amigable
        fecha = row.get("Fecha", "")
        fecha_valor = row.get("Fecha valor", "")
        concepto = row.get("Concepto", "")
        importe = row.get("Importe", "")
        saldo = row.get("Saldo Posterior", "")
        print(f"Fecha:        {fecha}")
        print(f"Fecha valor:  {fecha_valor}")
        print(f"Concepto:     {concepto}")
        print(f"Importe:      {importe}")
        print(f"Saldo Posterior: {saldo}")
    elif args.cmd == "bank-month":
        try:
            rows = _iter_bank_csv_rows(args.csv)
        except Exception as exc:
            print(f"Error leyendo CSV: {exc}")
            return
        # Filtra por mes YYYY-MM comparando con la columna 'Fecha' (DD/MM/YYYY)
        wanted = args.month
        filtered = []
        for row in rows:
            fecha_txt = row.get("Fecha", "").strip()
            if not fecha_txt:
                continue
            try:
                d = _parse_ddmmyyyy(fecha_txt)
            except Exception:
                continue
            ym = f"{d.year:04d}-{d.month:02d}"
            if ym == wanted:
                filtered.append(row)
        if not filtered:
            print(f"Sin movimientos para {wanted}.")
            return
        if args.raw:
            for r in filtered:
                print(r)
            return
        # Salida amigable + totales
        total = 0.0
        print(f"Movimientos {wanted}")
        print("-" * 74)
        for r in filtered:
            fecha = r.get("Fecha", "")
            concepto = r.get("Concepto", "")
            importe_txt = r.get("Importe", "")
            saldo = r.get("Saldo Posterior", "")
            importe_val = _parse_euro_amount(importe_txt)
            total += importe_val
            print(f"{fecha} | {concepto:<40} | Importe:{importe_val:10.2f} | Saldo:{saldo}")
        print("-" * 74)
        n_movs = len(filtered)
        print(f"{'Nº MOVIMIENTOS':<55} {n_movs:10d}")
        print(f"{'TOTAL MES':<55} {total:10.2f}")
    elif args.cmd == "bank-add":
        # 1) Leer el movimiento del CSV
        try:
            row = _read_bank_csv_row(args.csv, args.id)
        except Exception as exc:
            print(f"Error leyendo CSV: {exc}")
            return
        # 2) Mostrar info del movimiento
        print("Movimiento seleccionado:")
        print(f"  Fecha:        {row.get('Fecha', '')}")
        print(f"  Fecha valor:  {row.get('Fecha valor', '')}")
        print(f"  Concepto:     {row.get('Concepto', '')}")
        print(f"  Importe:      {row.get('Importe', '')}")
        print(f"  Saldo:        {row.get('Saldo Posterior', '')}")
        # 3) Sugerir valores para el asiento
        concepto_sug = row.get("Concepto", "").strip()
        # Fecha preferida según bandera
        fecha_txt = row.get(args.fecha_col, "").strip()
        try:
            fecha_sug = _parse_ddmmyyyy(fecha_txt).isoformat()
        except Exception:
            # Fallback: hoy
            fecha_sug = date.today().isoformat()
        importe_val = _parse_euro_amount(row.get("Importe", "0"))
        if importe_val < 0:
            debe_sug = 0.0
            haber_sug = abs(importe_val)
        else:
            debe_sug = importe_val
            haber_sug = 0.0
        # 4) Interactivo para confirmar/ajustar
        if args.no_interactive:
            fecha_final = fecha_sug
            concepto_final = concepto_sug
            debe_final = debe_sug
            haber_final = haber_sug
        else:
            print("\nIntroduce los datos del asiento (Enter para aceptar sugeridos):")
            fecha_final_str = _prompt_with_default("Fecha (YYYY-MM-DD)", fecha_sug)
            concepto_final = _prompt_with_default("Concepto", concepto_sug)
            debe_final_str = _prompt_with_default("Debe (número)", f"{debe_sug:.2f}")
            haber_final_str = _prompt_with_default("Haber (número)", f"{haber_sug:.2f}")
            # Normalizar/validar
            try:
                fecha_final = date.fromisoformat(fecha_final_str).isoformat()
            except Exception:
                print(f"Advertencia: fecha inválida '{fecha_final_str}', usando sugerida {fecha_sug}")
                fecha_final = fecha_sug
            try:
                debe_final = float(debe_final_str)
            except Exception:
                print(f"Advertencia: debe inválido '{debe_final_str}', usando sugerido {debe_sug:.2f}")
                debe_final = debe_sug
            try:
                haber_final = float(haber_final_str)
            except Exception:
                print(f"Advertencia: haber inválido '{haber_final_str}', usando sugerido {haber_sug:.2f}")
                haber_final = haber_sug
            # Asegurar no-negativos
            if debe_final < 0:
                print("Advertencia: 'Debe' no puede ser negativo. Forzando a 0.0")
                debe_final = 0.0
            if haber_final < 0:
                print("Advertencia: 'Haber' no puede ser negativo. Forzando a 0.0")
                haber_final = 0.0
        # 5) Crear y guardar el asiento vía servicios
        e = Entry(
            fecha=date.fromisoformat(fecha_final),
            concepto=concepto_final,
            debe=debe_final,
            haber=haber_final,
        )
        add_entry(storage, e)
        print("\nAsiento creado a partir del movimiento bancario:")
        print(f"  Fecha:    {e.fecha.isoformat()}")
        print(f"  Concepto: {e.concepto}")
        print(f"  Debe:     {e.debe:.2f}")
        print(f"  Haber:    {e.haber:.2f}")
        print("Asiento guardado.")