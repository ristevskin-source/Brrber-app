import streamlit as st
import sqlite3
from datetime import datetime, timedelta

RADNO_VREME = [(9,0), (20,0)]
INTERVAL_MIN = 60
BROJ_DANA = 7

def init_db():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rezervacije 
                 (id INTEGER PRIMARY KEY, usluga TEXT, datum TEXT, vreme TEXT, 
                  ime TEXT, telefon TEXT, cena INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cenovnik (usluga TEXT PRIMARY KEY, cena INTEGER)''')
    default_cene = [('Šišanje', 2000), ('Brijanje', 700), ('Stilizovanje', 1000)]
    c.executemany("INSERT OR IGNORE INTO cenovnik VALUES (?, ?)", default_cene)
    c.execute('''CREATE TABLE IF NOT EXISTS konfiguracija (lozinka TEXT)''')
    c.execute("SELECT * FROM konfiguracija")
    if not c.fetchone():
        c.execute("INSERT INTO konfiguracija (lozinka) VALUES ('1234')")
    conn.commit()
    conn.close()

init_db()

def generisi_datume():
    now = datetime.now()
    if now.hour >= 20:
        start = now + timedelta(days=1)
    else:
        start = now
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    datumi = []
    for i in range(BROJ_DANA):
        dan = start + timedelta(days=i)
        # 🔥 NOVO: formatiranje sa danom u nedelji
        dani_u_nedelji = ["Ponedeljak", "Utorak", "Sreda", "Četvrtak", "Petak", "Subota", "Nedelja"]
        dan_u_nedelji = dani_u_nedelji[dan.weekday()]
        datumi.append(f"{dan_u_nedelji}, {dan.strftime('%d.%m.%Y')}")
    return datumi

def generisi_termine_za_dan(datum_str):
    # 🔥 NOVO: Ako je nedelja, ne pravi termine
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    if dan.weekday() == 6:  # 6 = Nedelja
        return  # izlazi iz funkcije, ne pravi termine
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("DELETE FROM rezervacije WHERE datum=?", (datum_str,))
    # ... ostatak k 97oda ostaje isti ...
    sat_start, min_start = RADNO_VREME[0]
    sat_kraj, min_kraj = RADNO_VREME[1]
    trenutno = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_start, minute=min_start)
    kraj = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_kraj, minute=min_kraj)
    termini = []
    while trenutno < kraj:
        vreme = trenutno.strftime("%H:%M")
        termini.append((None, datum_str, vreme, None, None, None))
        trenutno += timedelta(minutes=INTERVAL_MIN)
    if termini:
        c.executemany("INSERT INTO rezervacije (usluga, datum, vreme, ime, telefon, cena) VALUES (?, ?, ?, ?, ?, ?)", termini)
        conn.commit()
    conn.close()

def osvezi_termine():
    datumi = generisi_datume()
    for d in datumi:
        generisi_termine_za_dan(d)

osvezi_termine()

st.title("💈 Zakazivanje termina")

with st.expander("🔑 Admin"):
    if "admin" not in st.session_state:
        st.session_state.admin = False
    if not st.session_state.admin:
        if st.text_input("Lozinka", type="password") == "1234":
            st.session_state.admin = True
            st.rerun()
    else:
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT sum(cena) FROM rezervacije WHERE ime IS NOT NULL")
        total = c.fetchone()[0] or 0
        st.write(f"Ukupno: {total} din")
        conn.close()

conn = sqlite3.connect('termini.db')
c = conn.cursor()
datumi = generisi_datume()
c.execute("SELECT usluga, cena FROM cenovnik")
cenovnik = dict(c.fetchall())
conn.close()

with st.form("zakazivanje"):
    ime = st.text_input("Ime i prezime *")
    tel = st.text_input("Telefon *")
    usluga = st.selectbox("Usluga", list(cenovnik.keys()))
    datum = st.selectbox("Datum", datumi)
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("SELECT vreme FROM rezervacije WHERE datum=? AND ime IS NULL", (datum,))
    slobodni = [r[0] for r in c.fetchall()]
    conn.close()
    if slobodni:
        termin = st.selectbox("Slobodan termin", slobodni)
        if st.form_submit_button("Zakaži"):
            cena = cenovnik[usluga]
            conn = sqlite3.connect('termini.db')
            c = conn.cursor()
            c.execute("UPDATE rezervacije SET ime=?, telefon=?, usluga=?, cena=? WHERE datum=? AND vreme=?", 
                      (ime, tel, usluga, cena, datum, termin))
            conn.commit()
            conn.close()
            st.success("✅ Uspešno zakazano!")
            st.rerun()
    else:
        st.warning("⏳ Nema slobodnih termina")
