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
    if 'datum_naplate' not in kolone:
        c.execute("ALTER TABLE rezervacije ADD COLUMN datum_naplate TEXT")
    
    # 🔥 POPUNI datum_naplate za stare naplaćene rezervacije (ako je NULL)
    c.execute("UPDATE rezervacije SET datum_naplate = datum WHERE naplaceno=1 AND datum_naplate IS NULL")
    
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
# 🔥 SLIKA (zaglavlje, pre naslova)
try:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("IMG-7dca0f9a0a28a9b8098a0cf36f04adb2-V.jpg", width=300)
except:
    pass

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
        # ---------- FINANSIJSKI IZVEŠTAJ ----------
        st.subheader("📊 Finansijski izveštaj")
        
        today = datetime.now().strftime("%Y-%m-%d")
        this_month = datetime.now().strftime("%Y-%m")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        
        # Promet za danas
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate=?", (today,))
        danas = c.fetchone()[0] or 0
        
        # Promet za tekući mesec
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE ?", (f"{this_month}%",))
        mesec = c.fetchone()[0] or 0
        
        # Ukupan promet (sve vreme)
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1")
        ukupno = c.fetchone()[0] or 0
        
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📅 Danas", f"{danas} din")
        with col2:
            st.metric("📆 Ovaj mesec", f"{mesec} din")
        with col3:
            st.metric("💰 Ukupno", f"{ukupno} din")
        
        # ---------- PREGLED PROMETA PO MESECIMA ----------
        st.subheader("📈 Promet po mesecima")
        
        # Dohvati sve dostupne mesece iz baze
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT substr(datum_naplate,1,7) FROM rezervacije WHERE naplaceno=1 AND datum_naplate IS NOT NULL ORDER BY datum_naplate DESC")
        dostupni_meseci = [row[0] for row in c.fetchall()]
        conn.close()
        
        if dostupni_meseci:
            izabrani_mesec = st.selectbox("Izaberite mesec", dostupni_meseci, index=0)
            
            conn = sqlite3.connect('termini.db')
            c = conn.cursor()
            c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE ?", (f"{izabrani_mesec}%",))
            promet_mesec = c.fetchone()[0] or 0
            conn.close()
            
            st.write(f"### Promet za {izabrani_mesec}: **{promet_mesec} din**")
        else:
            st.info("📭 Još uvek nema naplaćenih usluga.")
        
        # ---------- TABELA ZAKAZANIH KLIJENATA ----------
        st.subheader("📋 Zakazani klijenti")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("""
            SELECT id, ime, usluga, datum, vreme, cena, naplaceno 
            FROM rezervacije 
            WHERE ime IS NOT NULL 
            ORDER BY datum ASC, vreme ASC
        """)
        svi_klijenti = c.fetchall()
        conn.close()
        
        if svi_klijenti:
            st.markdown("---")
            col1, col2, col3, col4, col5, col6, col7 = st.columns([0.3, 1.8, 1.5, 1.2, 1.0, 1.0, 1.2])
            with col1: st.write("**#**")
            with col2: st.write("**Ime**")
            with col3: st.write("**Usluga**")
            with col4: st.write("**Datum**")
            with col5: st.write("**Vreme**")
            with col6: st.write("**Cena**")
            with col7: st.write("**Status**")
            st.markdown("---")
            
            for idx, red in enumerate(svi_klijenti, start=1):
                id, ime, usluga, datum, vreme, cena, naplaceno = red
                
                col1, col2, col3, col4, col5, col6, col7 = st.columns([0.3, 1.8, 1.5, 1.2, 1.0, 1.0, 1.2])
                with col1:
                    st.write(f"{idx}.")
                with col2:
                    st.write(ime)
                with col3:
                    st.write(usluga)
                with col4:
                    st.write(formatiraj_datum(datum))
                with col5:
                    st.write(vreme)
                with col6:
                    st.write(f"{cena} din")
                with col7:
                    if naplaceno == 1:
                        st.write("✅ Naplaćeno")
                    else:
                        if f"paid_{id}" not in st.session_state:
                            st.session_state[f"paid_{id}"] = False
                        
                        if st.session_state[f"paid_{id}"]:
                            st.write("⏳ Naplaćivanje...")
                        else:
                            if st.button(f"💰 Naplati", key=f"pay_{id}"):
                                conn = sqlite3.connect('termini.db')
                                c = conn.cursor()
                                c.execute("UPDATE rezervacije SET naplaceno=1, datum_naplate=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d"), id))
                                conn.commit()
                                conn.close()
                                st.session_state[f"paid_{id}"] = True
                                st.success(f"✅ Naplaćeno: {ime}")
                                st.rerun()
            st.markdown("---")
        else:
            st.info("📭 Trenutno nema zakazanih klijenata.")
        
        # ---------- UPRAVLJANJE USLUGAMA ----------
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
        
        # ---------- UPRAVLJANJE PAUZAMA ----------
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
