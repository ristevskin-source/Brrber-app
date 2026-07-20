import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# ---------- KONFIGURACIJA ----------
RADNO_VREME = [(9,0), (20,0)]
INTERVAL_MIN = 60
BROJ_DANA = 7

# ---------- INICIJALIZACIJA BAZE ----------
def init_db():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS rezervacije 
                 (id INTEGER PRIMARY KEY, usluga TEXT, datum TEXT, vreme TEXT, 
                  ime TEXT, telefon TEXT, cena INTEGER)''')
    
    c.execute("PRAGMA table_info(rezervacije)")
    kolone = [info[1] for info in c.fetchall()]
    if 'naplaceno' not in kolone:
        c.execute("ALTER TABLE rezervacije ADD COLUMN naplaceno INTEGER DEFAULT 0")
    
    c.execute('''CREATE TABLE IF NOT EXISTS cenovnik (usluga TEXT PRIMARY KEY, cena INTEGER)''')
    default_cene = [('Šišanje', 2000), ('Brijanje', 700), ('Stilizovanje', 1000)]
    c.executemany("INSERT OR IGNORE INTO cenovnik VALUES (?, ?)", default_cene)
    
    c.execute('''CREATE TABLE IF NOT EXISTS konfiguracija (lozinka TEXT)''')
    c.execute("SELECT * FROM konfiguracija")
    if not c.fetchone():
        c.execute("INSERT INTO konfiguracija (lozinka) VALUES ('1234')")
    
    c.execute('''CREATE TABLE IF NOT EXISTS pauze 
                 (id INTEGER PRIMARY KEY, datum TEXT, vreme TEXT, napomena TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# ---------- POMOĆNE FUNKCIJE ----------
def formatiraj_datum(datum_str):
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    dani_u_nedelji = ["Ponedeljak", "Utorak", "Sreda", "Četvrtak", "Petak", "Subota", "Nedelja"]
    return f"{dani_u_nedelji[dan.weekday()]}, {dan.strftime('%d.%m.%Y')}"

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
        datumi.append(dan.strftime("%Y-%m-%d"))
    return datumi

def generisi_termine_za_dan(datum_str):
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    if dan.weekday() == 6:
        return
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute("SELECT vreme FROM pauze WHERE datum=?", (datum_str,))
    pauze = [row[0] for row in c.fetchall()]
    
    c.execute("DELETE FROM rezervacije WHERE datum=? AND ime IS NULL", (datum_str,))
    
    sat_start, min_start = RADNO_VREME[0]
    sat_kraj, min_kraj = RADNO_VREME[1]
    trenutno = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_start, minute=min_start)
    kraj = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_kraj, minute=min_kraj)
    
    termini = []
    while trenutno < kraj:
        vreme = trenutno.strftime("%H:%M")
        if vreme not in pauze:
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

# ---------- UI ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("IMG_20260718_151846.jpg", width=300)

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
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1")
        total = c.fetchone()[0] or 0
        st.write(f"### 💰 Ukupan promet: {total} din")
        conn.close()
        
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
        
        st.subheader("📝 Upravljanje uslugama")
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
        
        st.subheader("⏸️ Pauze (blokirani termini)")
        with st.form("dodaj_pauzu"):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                datum_pauze = st.selectbox("Datum", generisi_datume(), format_func=formatiraj_datum)
            with col2:
                conn = sqlite3.connect('termini.db')
                c = conn.cursor()
                c.execute("SELECT vreme FROM rezervacije WHERE datum=? AND ime IS NULL", (datum_pauze,))
                slobodna_vremena = [r[0] for r in c.fetchall()]
                conn.close()
                if slobodna_vremena:
                    vreme_pauze = st.selectbox("Vreme", slobodna_vremena)
                else:
                    vreme_pauze = st.text_input("Vreme (HH:MM)")
            with col3:
                napomena = st.text_input("Napomena")
            if st.form_submit_button("➕ Dodaj pauzu"):
                if datum_pauze and vreme_pauze:
                    conn = sqlite3.connect('termini.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO pauze (datum, vreme, napomena) VALUES (?, ?, ?)", 
                              (datum_pauze, vreme_pauze, napomena or "Pauza"))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Pauza dodata za {datum_pauze} u {vreme_pauze}")
                    st.rerun()
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT id, datum, vreme, napomena FROM pauze ORDER BY datum, vreme")
        sve_pauze = c.fetchall()
        conn.close()
        
        if sve_pauze:
            for id, datum, vreme, napomena in sve_pauze:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{formatiraj_datum(datum)}** {vreme}")
                with col2:
                    st.write(napomena if napomena else "Pauza")
                with col3:
                    if st.button(f"🗑️ Obriši", key=f"del_pauza_{id}"):
                        conn = sqlite3.connect('termini.db')
                        c = conn.cursor()
                        c.execute("DELETE FROM pauze WHERE id=?", (id,))
                        conn.commit()
                        conn.close()
                        st.success("🗑️ Pauza obrisana!")
                        st.rerun()
        else:
            st.info("📭 Trenutno nema zakazanih pauza.")

# ---------- FORMA ZA KLIJENTE ----------
if 'booking_success' not in st.session_state:
    st.session_state['booking_success'] = False

if st.session_state['booking_success']:
    detalji = st.session_state['booking_details']
    st.balloons()
    st.success("✅ **Uspešno ste zakazali termin!**")
    st.markdown(f"""
    📋 **Usluga:** {detalji['usluga']}  
    📅 **Datum:** {formatiraj_datum(detalji['datum'])}  
    ⏰ **Vreme:** {detalji['vreme']}  
    💰 **Cena:** {detalji['cena']} din  
    👤 **Klijent:** {detalji['ime']}  
    
    ✂️ **Vidimo se!**
    """)
    if st.button("📅 Zakaži novi termin"):
        st.session_state['booking_success'] = False
        st.rerun()
else:
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    datumi_raw = generisi_datume()
    c.execute("SELECT usluga, cena FROM cenovnik")
    cenovnik_dict = dict(c.fetchall())
    conn.close()
    
    if datumi_raw and cenovnik_dict:
        with st.form("klijent_forma"):
            ime = st.text_input("Ime i prezime *")
            tel = st.text_input("Telefon *")
            usluga = st.selectbox("Usluga", list(cenovnik_dict.keys()))
            datum = st.selectbox("Datum", datumi_raw, format_func=formatiraj_datum)
            
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
                    
                    st.session_state['booking_success'] = True
                    st.session_state['booking_details'] = {
                        'usluga': usluga,
                        'datum': datum,
                        'vreme': termin,
                        'cena': cena,
                        'ime': ime
                    }
                    st.rerun()
            else:
                st.warning("⏳ Nema slobodnih termina za izabrani datum.")
    else:
        st.error("❌ Baza je prazna.")
