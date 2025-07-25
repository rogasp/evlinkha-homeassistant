# Uppgifter för EVLinkHA-komponenten

Denna mapp innehåller filer för att hantera arbetsuppgifter relaterade till EVLinkHA Home Assistant-komponenten.

## Exempel på uppgiftsfil:

```markdown
### Uppgift: Implementera stöd för ny fordonstyp

**Beskrivning:** Lägg till logik i `api.py` och `sensor.py` för att hantera en ny fordonstyp som EVLinkHA-tjänsten nu stöder. Detta inkluderar att parsa nya datafält och skapa relevanta sensorer.

**Prioritet:** Hög

**Status:** Öppen

**Tilldelad:** [Namn]

**Checklista:**
- [ ] Uppdatera `api.py` för att hantera nya API-svar.
- [ ] Lägg till nya konstanter i `const.py` om nödvändigt.
- [ ] Uppdatera `sensor.py` för att skapa nya sensorer baserat på den nya datan.
- [ ] Skriv enhetstester för den nya logiken.
- [ ] Uppdatera dokumentation (om relevant).
```

Skapa nya `.md`-filer för varje större uppgift eller funktion som ska implementeras.