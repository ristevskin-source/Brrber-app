import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# ---------- KONFIGURACIJA ----------
RADNO_VREME = [(9,0), (20,0)]  # od 09:00 do 20:00
INTERVAL_MIN = 60              # na svakih sat vremena
BROJ_DANA = 7                  # prikazujemo 7 dana

# ---------- INICIJALIZACIJA BAZE ----------
def init_db():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    # Glavna tabela
    c.execute('''CREATE TABLE IF NOT EXISTS rezervacije 
                 (id INTEGER PRIMARY KEY, usluga TEXT, datum TEXT, vreme TEXT, 
                  ime TEXT, telefon TEXT, cena INTEGER)''')
    
    # Dodaj kolonu "naplaceno" ako ne postoji
    c.execute("PRAGMA table_info(rezervacije)")
    kolone = [info[1] for info in c.fetchall()]
    if 'naplaceno' not in kolone:
        c.execute("ALTER TABLE rezervacije ADD COLUMN naplaceno INTEGER DEFAULT 0")
    
    # Cenovnik
    c.execute('''CREATE TABLE IF NOT EXISTS cenovnik (usluga TEXT PRIMARY KEY, cena INTEGER)''')
    default_cene = [('Šišanje', 2000), ('Brijanje', 700), ('Stilizovanje', 1000)]
    c.executemany("INSERT OR IGNORE INTO cenovnik VALUES (?, ?)", default_cene)
    
    # Lozinka
    c.execute('''CREATE TABLE IF NOT EXISTS konfiguracija (lozinka TEXT)''')
    c.execute("SELECT * FROM konfiguracija")
    if not c.fetchone():
        c.execute("INSERT INTO konfiguracija (lozinka) VALUES ('1234')")
    
    conn.commit()
    conn.close()

init_db()

# ---------- POMOĆNE FUNKCIJE ----------
def formatiraj_datum(datum_str):
    """Pretvara YYYY-MM-DD u 'Ponedeljak, 20.07.2026.'"""
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    dani_u_nedelji = ["Ponedeljak", "Utorak", "Sreda", "Četvrtak", "Petak", "Subota", "Nedelja"]
    return f"{dani_u_nedelji[dan.weekday()]}, {dan.strftime('%d.%m.%Y')}"

def generisi_datume():
    """Vraća listu od 7 datuma (YYYY-MM-DD) sa pomeranjem u 20h"""
    now = datetime.now()
    if now.hour >= 20:
        start = now + timedelta(days=1)
    else:
        start = now
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    datumi = []
    for i in range(BROJ_DANA):
        dan = start + timedelta(days=i)
        datumi.append(dan.strftime("%Y-%m-%d"))
    return datumi

def generisi_termine_za_dan(datum_str):
    """Kreira termine za dati dan (osim ako je NEDELJA)"""
    # ⛔ Ako je Nedelja (weekday() == 6) - ne pravi termine
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    if dan.weekday() == 6:
        return  # Nedelja je neradna, izlazi iz funkcije
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    # Brišem stare pa dodajem nove
    c.execute("DELETE FROM rezervacije WHERE datum=?", (datum_str,))
    
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
    """Generiši termine za sve datume u kliznom prozoru"""
    datumi = generisi_datume()
    for d in datumi:
        generisi_termine_za_dan(d)

osvezi_termine()

# ---------- UI ----------
st.title("💈 Zakazivanje termina")

# ---------- ADMIN PANEL ----------
with st.expander("🔑 Admin"):
    if "admin" not in st.session_state:
        st.session_state.admin = False
    
    if not st.session_state.admin:
        lozinka = st.text_input("Lozinka:", type="password")
        if lozinka == "1234":
            st.session_state.admin = True
            st.rerun()
    else:
        # 📊 Finansijski izveštaj (samo naplaćeni)
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1")
        total = c.fetchone()[0] or 0
        st.write(f"### 💰 Ukupan promet: {total} din")
        conn.close()
        
        # 💳 Potvrdi naplatu (lista klijenata koji čekaju)
        st.subheader("💳 Potvrdi naplatu")
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT id, ime, usluga, datum, vreme, cena FROM rezervacije WHERE ime IS NOT NULL AND (naplaceno IS NULL OR naplaceno=0)")
        cekanje_naplate = c.fetchall()
        conn.close()
        
        if cekanje_naplate:
            for red in cekanje_naplate:
                id, ime, usluga, datum, vreme, cena = red
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{ime}** - {usluga} ({datum} {vreme})")
                with col2:
                    st.write(f"{cena} din")
                with col3:
                    if st.button(f"✅ Naplati", key=f"pay_{id}"):
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("UPDATE rezervacije SET naplaceno=1 WHERE id=?", (id,))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Naplaćeno: {ime}")
                        st.rerun()
        else:
            st.info("📭 Svi klijenti su naplaćeni.")
        
        # 📝 Upravljanje uslugama (dodavanje i izmena cena)
        st.subheader("📝 Upravljanje uslugama")
        
        # Dodavanje nove usluge
        with st.form("dodaj_uslugu"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                nova_usluga = st.text_input("Naziv nove usluge")
            with col2:
                nova_cena = st.number_input("Cena (din)", min_value=0, step=100)
            with col3:
                if st.form_submit_button("➕ Dodaj"):
                    if nova_usluga and nova_cena > 0:
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("INSERT OR IGNORE INTO cenovnik VALUES (?, ?)", (nova_usluga, nova_cena))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Dodato: {nova_usluga} - {nova_cena} din")
                        st.rerun()
        
        # Pregled i izmena postojećih usluga
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT usluga, cena FROM cenovnik")
        sve_usluge = c.fetchall()
        conn.close()
        
        for usluga, cena in sve_usluge:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{usluga}**")
            with col2:
                st.write(f"{cena} din")
            with col3:
                nova_cena = st.number_input(f"Nova cena", value=cena, step=100, key=f"cena_{usluga}")
                if st.button(f"💾 Sačuvaj", key=f"save_{usluga}"):
                    conn = sqlite3.connect('termini.db')
                    c = conn.cursor()
                    c.execute("UPDATE cenovnik SET cena=? WHERE usluga=?", (nova_cena, usluga))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Cena za {usluga} ažurirana!")
                    st.rerun()

# ---------- FORMA ZA KLIJENTE ----------
conn = sqlite3.connect('termini.db')
c = conn.cursor()

# Dinamički datumi (7 dana) - prikazujemo ih lepo formatirane
datumi_raw = generisi_datume()

# Cenovnik
c.execute("SELECT usluga, cena FROM cenovnik")
cenovnik_dict = dict(c.fetchall())
conn.close()

if datumi_raw and cenovnik_dict:
    with st.form("klijent_forma"):
        ime = st.text_input("Ime i prezime *")
        tel = st.text_input("Telefon *")
        usluga = st.selectbox("Usluga", list(cenovnik_dict.keys()))
        
        # 🔥 Prikazujemo datume sa danima u nedelji
        datum = st.selectbox(
            "Datum", 
            datumi_raw, 
            format_func=formatiraj_datum
        )
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT id, vreme FROM rezervacije WHERE datum=? AND ime IS NULL", (datum,))
        slobodni = c.fetchall()
        conn.close()
        
        if slobodni:
            mapa = {t[1]: t[0] for t in slobodni}
            termin = st.selectbox("Slobodan termin", list(mapa.keys()))
            
            if st.form_submit_button("Zakaži"):
                cena = cenovnik_dict[usluga]
                conn = sqlite3.connect('termini.db')
                c = conn.cursor()
                c.execute("UPDATE rezervacije SET ime=?, telefon=?, usluga=?, cena=? WHERE id=?", 
                          (ime, tel, usluga, cena, mapa[termin]))
                conn.commit()
                conn.close()
                st.success(f"✅ Uspešno zakazano: {usluga} ({cena} din).")
                st.rerun()
        else:
            st.warning("⏳ Nema slobodnih termina za izabrani datum.")
else:
    st.error("❌ Baza je prazna.")
