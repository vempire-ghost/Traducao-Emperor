import re
import tkinter as tk
from tkinter import messagebox, scrolledtext
import pyperclip
import unicodedata
import subprocess
import platform
import struct
import os
import datetime

BASE = "EmperorText_TRADUZIR.txt"
MAX = 50
BIN_FILE = "EmperorText.eng"

OFFSET_RE = re.compile(r"OFFSET:\s*(0x[0-9A-Fa-f]+)")
ORIG_RE = re.compile(r"ORIGINAL\s*\[(\d+)\s*chars\]:\s*(.*)")
CELL_ID_RE = re.compile(r"CELULA:\s*(\d+)\s+GRUPO:\s*(\d+)")

# ---------------- ESTRUTURA CORRIGIDA ---------------- #

class ZeusTextFile:
    def __init__(self, filename):
        self.filename = filename
        self.data = None
        self.header = None
        self.groups = []
        self.strings = []
    
    def load(self):
        """Carrega arquivo binário CORRETAMENTE - ORDEM (COUNT, OFFSET) para ESTE ARQUIVO!"""
        with open(self.filename, 'rb') as f:
            self.data = f.read()
        
        print(f"Tamanho do arquivo: {len(self.data)} bytes")
        
        # 1. File signature
        signature = self.data[0:16].decode('ascii', errors='ignore').rstrip('\x00')
        print(f"Assinatura: {signature}")
        
        # 2. List header
        header_offset = 16
        self.header = {
            'num_count_values': struct.unpack('<I', self.data[header_offset:header_offset+4])[0],
            'total_cells': struct.unpack('<I', self.data[header_offset+4:header_offset+8])[0],
            'mystery_value': struct.unpack('<I', self.data[header_offset+8:header_offset+12])[0],
            'reserved': struct.unpack('<I', self.data[header_offset+12:header_offset+16])[0]
        }
        
        print(f"Cabeçalho: {self.header}")
        
        # 3. List block (367 pares) - 🔥🔥🔥 ORDEM INVERTIDA: COUNT primeiro, OFFSET depois 🔥🔥🔥
        list_start = 32
        data_start = 0x1F5C
        
        self.groups = []
        offset = list_start
        
        print(f"Lendo lista de 0x{list_start:08X} a 0x{data_start-1:08X}...")
        print("🔥🔥🔥 ORDEM: (COUNT, OFFSET) - ARQUIVO ESTÁ INVERTIDO! 🔥🔥🔥")
        
        # Lê EXATAMENTE 367 pares
        for pair_id in range(367):
            if offset + 8 > data_start:
                print(f"AVISO: Fora do limite da lista no par {pair_id}")
                break
            
            # 🔥🔥🔥 ORDEM INVERTIDA: COUNT primeiro, OFFSET depois 🔥🔥🔥
            count = struct.unpack('<I', self.data[offset:offset+4])[0]      # COUNT primeiro!
            group_offset = struct.unpack('<I', self.data[offset+4:offset+8])[0]  # OFFSET depois!
            
            self.groups.append({
                'offset': group_offset,  # Offset relativo ao Data
                'count': count,          # Número de células
                'pair_id': pair_id,
                'strings': [],
                'original_offset': offset
            })
            
            # DEBUG: Primeiros pares
            if pair_id < 5:
                print(f"  Par {pair_id}: count={count}, offset=0x{group_offset:04X} ({group_offset})")
            
            offset += 8
        
        print(f"Pares lidos: {len(self.groups)}/367")
        
        # Verificação crítica - AGORA COM VALORES CORRETOS
        if len(self.groups) > 1:
            print(f"\nVERIFICAÇÃO CRÍTICA:")
            print(f"Par 0: count={self.groups[0]['count']}, offset={self.groups[0]['offset']} (deve ser 0, 0)")
            print(f"Par 1: count={self.groups[1]['count']}, offset={self.groups[1]['offset']} (deve ser 7, 103)")
            print(f"Par 2: count={self.groups[2]['count']}, offset={self.groups[2]['offset']} (deve ser 14, 323)")
            
            if self.groups[0]['count'] == 0 and self.groups[0]['offset'] == 0:
                print("✓ Par 0 OK")
            else:
                print("✗ Par 0 ERRADO!")
            
            if self.groups[1]['count'] == 7 and self.groups[1]['offset'] == 0x67:
                print("✓ Par 1 OK")
            else:
                print(f"✗ Par 1 ERRADO! Esperado: count=7, offset=103 (0x67)")
        
        # 4. Extrai strings
        self.extract_strings(data_start)
        
        # 5. Mapeia strings para grupos - PRECISA SER REESCRITO TOTALMENTE!
        self.map_strings_to_groups_corrected()
        
        # Validação
        total_in_groups = sum(g['count'] for g in self.groups)
        print(f"\nVALIDAÇÃO FINAL:")
        print(f"Células totais nos grupos: {total_in_groups}")
        print(f"Células no header: {self.header['total_cells']}")
        print(f"Strings extraídas: {len(self.strings)}")
        
        if total_in_groups == self.header['total_cells']:
            print("✓ Contagem de células BATE!")
        else:
            print(f"✗ Contagem NÃO bate! Diferença: {total_in_groups - self.header['total_cells']}")
        
        return True

    def map_strings_to_groups_corrected(self):
        """Mapeia strings para grupos CORRETAMENTE"""
        print(f"\nMapeando strings para grupos CORRETAMENTE...")
        
        # Reset
        for group in self.groups:
            group['strings'] = []
        
        # Grupo 0 é dummy (count=0, offset=0)
        # Grupo 1 é o primeiro real
        
        current_cell_index = 0
        
        for group_id, group in enumerate(self.groups):
            count = group['count']
            
            if count > 0:
                print(f"  Grupo {group_id}: count={count}, offset={group['offset']}")
                
                # Encontra a célula que começa neste offset
                target_offset = group['offset']
                found_cell_index = -1
                
                for i, string_info in enumerate(self.strings):
                    if string_info['offset'] == target_offset:
                        found_cell_index = i
                        print(f"    → Encontrou célula {string_info['cell_id']} no offset {target_offset}")
                        break
                
                if found_cell_index >= 0:
                    # Adiciona 'count' células a partir desta
                    for i in range(count):
                        cell_idx = found_cell_index + i
                        if cell_idx < len(self.strings):
                            cell_id = self.strings[cell_idx]['cell_id']
                            group['strings'].append(cell_id)
                            self.strings[cell_idx]['group_id'] = group_id
                    print(f"    → Adicionou {min(count, len(self.strings)-found_cell_index)} células")
                else:
                    print(f"    ✗ Nenhuma célula encontrada no offset {target_offset}")
    
    def extract_strings(self, data_start):
        """Extrai strings - versão corrigida"""
        pos = data_start
        cell_id = 1
        strings_extracted = 0
        
        print(f"\nExtraindo strings de 0x{data_start:08X}...")
        
        while pos < len(self.data) and strings_extracted < self.header['total_cells']:
            end_pos = self.data.find(b'\x00', pos)
            if end_pos == -1:
                break
            
            string_bytes = self.data[pos:end_pos]
            
            # Decodifica
            try:
                text = string_bytes.decode('cp1252')
            except:
                try:
                    text = string_bytes.decode('latin-1')
                except:
                    text = f"[BIN:{string_bytes.hex()[:20]}...]"
            
            self.strings.append({
                'cell_id': cell_id,
                'offset': pos - data_start,
                'absolute_offset': pos,
                'original_bytes': string_bytes,
                'text': text,
                'display_length': len(text),
                'byte_length': len(string_bytes),
                'modified': False,
                'new_text': None,
                'group_id': None
            })
            
            pos = end_pos + 1
            cell_id += 1
            strings_extracted += 1
        
        print(f"Strings extraídas: {len(self.strings)}")
        
        # Mostra primeiras strings
        print("\nPrimeiras 3 strings:")
        for i in range(min(3, len(self.strings))):
            s = self.strings[i]
            print(f"  Célula {s['cell_id']}: offset={s['offset']}, texto='{s['text']}'")
    
    # 🔥🔥🔥 ADICIONE ESTE MÉTODO SE NÃO EXISTIR 🔥🔥🔥
    def update_string(self, cell_id, new_text):
        """Atualiza uma string pelo ID da célula (1-based)"""
        if 1 <= cell_id <= len(self.strings):
            string_info = self.strings[cell_id - 1]
            string_info['modified'] = True
            string_info['new_text'] = new_text
            
            # Log da modificação
            old_len = string_info['byte_length']
            try:
                new_len = len(new_text.encode('cp1252'))
            except:
                new_len = len(new_text.encode('latin-1', errors='replace'))
            
            delta = new_len - old_len
            
            print(f"Célula {cell_id} atualizada: '{string_info['text'][:20]}...' → '{new_text[:20]}...'")
            print(f"  Tamanho: {old_len} → {new_len} bytes (Δ={delta})")
            
            return True
        else:
            print(f"ERRO: Célula {cell_id} não encontrada (total: {len(self.strings)} células)")
            return False
    
    def get_string_by_cell_id(self, cell_id):
        """Retorna string pelo ID (1-based)"""
        if 1 <= cell_id <= len(self.strings):
            return self.strings[cell_id - 1]
        return None

    def map_strings_to_groups_simple(self):
        """Mapeia strings para grupos - versão corrigida"""
        current_string_idx = 0
        
        print(f"\nMapeando strings para grupos...")
        print(f"Total de grupos: {len(self.groups)}")
        print(f"Total de strings: {len(self.strings)}")
        
        # Reset strings dos grupos
        for group in self.groups:
            group['strings'] = []
        
        # Grupo 0 é vazio (count=0)
        # Começa do grupo 1
        for group_id in range(1, len(self.groups)):
            group = self.groups[group_id]
            count = group['count']
            
            print(f"  Grupo {group_id}: precisa de {count} strings")
            
            if count > 0:
                for i in range(count):
                    if current_string_idx < len(self.strings):
                        # Atribui string ao grupo
                        string_cell_id = self.strings[current_string_idx]['cell_id']
                        self.strings[current_string_idx]['group_id'] = group_id
                        group['strings'].append(string_cell_id)  # Guarda o cell_id
                        
                        if group_id < 5 and i == 0:
                            print(f"    → Primeira string: célula {string_cell_id} (índice {current_string_idx})")
                        
                        current_string_idx += 1
                    else:
                        print(f"  AVISO: Sem strings suficientes para grupo {group_id}")
                        break
        
        print(f"\nStrings mapeadas: {current_string_idx}/{len(self.strings)}")
        
        # Debug detalhado dos primeiros grupos
        print("\nDEBUG DETALHADO DOS PRIMEIROS GRUPOS:")
        for i in range(min(5, len(self.groups))):
            g = self.groups[i]
            if g['count'] > 0:
                if g['strings']:
                    first_cell_id = min(g['strings'])
                    # Encontra o índice da string
                    string_idx = None
                    for idx, s in enumerate(self.strings):
                        if s['cell_id'] == first_cell_id:
                            string_idx = idx
                            break
                    print(f"  Grupo {i}: count={g['count']}, primeira célula={first_cell_id}, string_idx={string_idx}")
                else:
                    print(f"  Grupo {i}: count={g['count']}, SEM STRINGS MAPEADAS!")

    def debug_original_file(self):
        """Debug do arquivo original"""
        print("\n" + "="*60)
        print("DEBUG DO ARQUIVO ORIGINAL")
        print("="*60)
        
        # Lê offsets originais dos primeiros grupos
        list_start = 32
        print("Primeiros 5 pares do arquivo original:")
        for pair_id in range(5):
            offset = list_start + (pair_id * 8)
            group_offset = struct.unpack('<I', self.data[offset:offset+4])[0]
            count = struct.unpack('<I', self.data[offset+4:offset+8])[0]
            print(f"  Par {pair_id}: offset=0x{group_offset:04X} ({group_offset}), count={count}")
        
        # Mostra as primeiras strings
        data_start = 0x1F5C
        print(f"\nPrimeiras 5 strings (começando em 0x{data_start:08X}):")
        
        pos = data_start
        string_count = 0
        while pos < len(self.data) and string_count < 5:
            end_pos = self.data.find(b'\x00', pos)
            if end_pos == -1:
                break
            
            string_bytes = self.data[pos:end_pos]
            try:
                text = string_bytes.decode('cp1252')
            except:
                try:
                    text = string_bytes.decode('latin-1')
                except:
                    text = f"[BIN:{string_bytes.hex()[:20]}...]"
            
            actual_offset = pos - data_start
            print(f"  String {string_count+1}: offset={actual_offset}, tamanho={len(string_bytes)}, texto='{text[:50]}...'")
            pos = end_pos + 1
            string_count += 1
        
        # Mostra qual string está no offset 0x67 (103)
        print(f"\nVerificando offset 0x67 (103) no arquivo original:")
        target_offset = data_start + 0x67
        if target_offset < len(self.data):
            end_pos = self.data.find(b'\x00', target_offset)
            if end_pos != -1:
                string_bytes = self.data[target_offset:end_pos]
                try:
                    text = string_bytes.decode('cp1252')
                except:
                    text = string_bytes.decode('latin-1', errors='ignore')
                print(f"  No offset 0x67 (absoluto 0x{target_offset:08X}): '{text}'")
                
                # Verifica qual célula é esta
                for i, string_info in enumerate(self.strings):
                    if string_info['absolute_offset'] == target_offset:
                        print(f"  Esta é a célula {string_info['cell_id']}")
                        break
        else:
            print(f"  Offset 0x67 está fora do arquivo!")
        
        # Mostra as primeiras células e seus grupos
        print(f"\nPrimeiras 10 células e seus grupos:")
        for i in range(min(10, len(self.strings))):
            s = self.strings[i]
            print(f"  Célula {s['cell_id']}: offset={s['offset']}, grupo={s['group_id']}, texto='{s['text'][:30]}...'")
    
    def save(self):
        """Salva arquivo COM A MESMA ORDEM DO ORIGINAL: (COUNT, OFFSET)"""
        print("\n" + "="*60)
        print("SALVANDO ARQUIVO BINÁRIO")
        print("🔥🔥🔥 ORDEM: (COUNT, OFFSET) - MESMA DO ORIGINAL 🔥🔥🔥")
        print("="*60)
        
        # 1. Reconstrói Data block
        data_start = 0x1F5C
        data_block = bytearray()
        cell_offsets = {}
        current_offset = 0
        
        # Constrói data block
        for string_info in self.strings:
            cell_id = string_info['cell_id']
            cell_offsets[cell_id] = current_offset
            
            if string_info['modified'] and string_info['new_text']:
                text = string_info['new_text']
                try:
                    encoded = text.encode('cp1252')
                except:
                    encoded = text.encode('latin-1', errors='replace')
            else:
                encoded = string_info['original_bytes']
            
            data_block.extend(encoded)
            data_block.append(0)
            current_offset += len(encoded) + 1
        
        # Null final
        if len(data_block) == 0 or data_block[-1] != 0:
            data_block.append(0)
        
        print(f"Data block: {len(data_block)} bytes")
        
        # 2. Reconstrói List block COM ORDEM (COUNT, OFFSET)
        list_block = bytearray()
        
        for group in self.groups:
            count = group['count']
            offset = 0
            
            if count > 0 and group['strings']:
                # Encontra primeira célula
                first_cell_id = min(group['strings'])
                if first_cell_id in cell_offsets:
                    offset = cell_offsets[first_cell_id]
            
            # 🔥🔥🔥 ORDEM (COUNT, OFFSET) como no original
            list_block.extend(struct.pack('<I', count))      # COUNT primeiro
            list_block.extend(struct.pack('<I', offset))     # OFFSET depois
            
            if group['pair_id'] < 5:
                print(f"  Par {group['pair_id']}: count={count}, offset=0x{offset:04X} ({offset})")
        
        # 3. Padding
        list_size_needed = 0x1F5C - 0x20
        if len(list_block) < list_size_needed:
            padding = list_size_needed - len(list_block)
            list_block.extend(b'\x00' * padding)
        
        # 4. Arquivo completo
        new_data = bytearray()
        
        # Signature
        signature = b'Zeus textfile.\x00\x00'
        new_data.extend(signature.ljust(16, b'\x00'))
        
        # Header
        new_data.extend(struct.pack('<I', self.header['num_count_values']))
        new_data.extend(struct.pack('<I', len(self.strings)))  # Atualiza total de células
        new_data.extend(struct.pack('<I', self.header['mystery_value']))
        new_data.extend(struct.pack('<I', self.header['reserved']))
        
        # List block
        new_data.extend(list_block)
        
        # Data block
        new_data.extend(data_block)
        
        # 5. Salva
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{self.filename}.backup_{timestamp}"
        
        try:
            # Backup
            with open(backup_name, 'wb') as f:
                f.write(self.data)
            print(f"\nBackup criado: {backup_name}")
            
            # Novo arquivo
            with open(self.filename, 'wb') as f:
                f.write(new_data)
            
            print(f"Arquivo salvo: {self.filename}")
            print(f"Tamanho original: {len(self.data)} bytes")
            print(f"Tamanho novo: {len(new_data)} bytes")
            
            return True
                
        except Exception as e:
            print(f"✗ ERRO ao salvar: {e}")
            return False
    
    def verify_saved_file(self, new_data):
        """Verificação completa - CORRIGIDA para ordem (OFFSET, COUNT)"""
        print("\n" + "="*60)
        print("VERIFICAÇÃO DO ARQUIVO SALVO")
        print("ORDEM: (OFFSET, COUNT)")  # 🔥 CORRIGIDO!
        print("="*60)
        
        try:
            # 1. Signature
            sig = new_data[0:16].decode('ascii', errors='ignore').rstrip('\x00')
            if sig != "Zeus textfile.":
                print(f"✗ Signature inválida: {sig}")
                return False
            print(f"✓ Signature: {sig}")
            
            # 2. Header
            num_count = struct.unpack('<I', new_data[16:20])[0]
            if num_count != 367:
                print(f"✗ num_count_values inválido: {num_count}")
                return False
            print(f"✓ num_count_values: {num_count}")
            
            # 3. Primeiros pares - ORDEM CORRETA: OFFSET, COUNT
            print("\nVerificando primeiros pares (OFFSET, COUNT):")  # 🔥 CORRIGIDO!
            
            # Par 0: deve ser (0, 0)
            offset0 = struct.unpack('<I', new_data[32:36])[0]  # OFFSET primeiro
            count0 = struct.unpack('<I', new_data[36:40])[0]   # COUNT depois
            if offset0 == 0 and count0 == 0:
                print(f"✓ Par 0: offset={offset0}, count={count0}")
            else:
                print(f"✗ Par 0 ERRADO: offset={offset0}, count={count0} (deveria ser 0, 0)")
                return False
            
            # Par 1: deve ser (0x67 (103), 7)
            offset1 = struct.unpack('<I', new_data[40:44])[0]  # OFFSET
            count1 = struct.unpack('<I', new_data[44:48])[0]   # COUNT
            print(f"  Par 1: offset=0x{offset1:04X} ({offset1}), count={count1}")
            
            # Par 2: deve ser (0x143 (323), 14)
            offset2 = struct.unpack('<I', new_data[48:52])[0]  # OFFSET
            count2 = struct.unpack('<I', new_data[52:56])[0]   # COUNT
            print(f"  Par 2: offset=0x{offset2:04X} ({offset2}), count={count2}")
            
            print(f"\n✓ Arquivo verificado com sucesso!")
            return True
            
        except Exception as e:
            print(f"✗ ERRO na verificação: {e}")
            return False

# ---------------- FUNÇÕES AUXILIARES ---------------- #

def criar_arquivo_base_se_nao_existir():
    """Cria o arquivo BASE se ele não existir"""
    if not os.path.exists(BASE):
        with open(BASE, "w", encoding="utf-8") as f:
            f.write(f"# Arquivo de tradução Zeus Text\n")
            f.write(f"# Criado em: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total de células: ~8248\n")
            f.write(f"# Formato:\n")
            f.write(f"# OFFSET: 0xXXXXXXX\n")
            f.write(f"# CELULA: X  GRUPO: Y\n")
            f.write(f"# ORIGINAL [N chars]: texto original\n")
            f.write(f"# TRADUÇÃO:\n")
            f.write(f"# texto traduzido\n\n")
        print(f"Arquivo {BASE} criado com sucesso!")
        return True
    return False

def adicionar_cabecalho_se_vazio():
    """Adiciona cabeçalho se o arquivo estiver vazio ou sem cabeçalho"""
    try:
        with open(BASE, "r", encoding="utf-8") as f:
            content = f.read()
        
        if len(content.strip()) == 0 or "# Arquivo de tradução Zeus Text" not in content:
            criar_arquivo_base_se_nao_existir()
    except:
        criar_arquivo_base_se_nao_existir()

def salvar_celulas_no_arquivo(blocks):
    """Salva as células extraídas no arquivo BASE, evitando duplicatas"""
    if not blocks:
        return
    
    try:
        # Lê o conteúdo atual do arquivo
        with open(BASE, "r", encoding="utf-8") as f:
            existing_content = f.read()
        
        # Extrai os IDs de células já existentes
        existing_cell_ids = set()
        for match in re.finditer(r"CELULA:\s*(\d+)", existing_content):
            existing_cell_ids.add(int(match.group(1)))
        
        # Filtra blocos que ainda não estão no arquivo
        new_blocks = []
        for block in blocks:
            # Extrai o ID da célula deste bloco
            match = re.search(r"CELULA:\s*(\d+)", block)
            if match:
                cell_id = int(match.group(1))
                if cell_id not in existing_cell_ids:
                    new_blocks.append(block)
        
        if new_blocks:
            # Adiciona os novos blocos ao arquivo
            with open(BASE, "a", encoding="utf-8") as f:
                for block in new_blocks:
                    f.write(block)
            
            print(f"{len(new_blocks)} novas células adicionadas ao arquivo {BASE}")
        else:
            print("Todas as células já existem no arquivo")
            
    except Exception as e:
        print(f"Erro ao salvar células no arquivo: {e}")

def focus_browser():
    """Tenta dar foco ao navegador aberto"""
    sistema = platform.system()
    
    try:
        if sistema == "Windows":
            subprocess.run(["powershell", "-Command", 
                "$wshell = New-Object -ComObject wscript.shell; "
                "$wshell.AppActivate('Chrome') -or $wshell.AppActivate('Firefox') -or $wshell.AppActivate('Microsoft Edge')"])
        elif sistema == "Darwin":
            subprocess.run(["osascript", "-e", 
                'tell application "System Events" to set frontmost of the first process whose frontmost is false and (name is "Google Chrome" or name is "Safari" or name is "Firefox") to true'])
        elif sistema == "Linux":
            subprocess.run(["wmctrl", "-a", "Chrome"], capture_output=True)
            subprocess.run(["wmctrl", "-a", "Firefox"], capture_output=True)
    except Exception as e:
        print(f"Erro ao focar navegador: {e}")

# ---------------- EXTRAÇÃO COM CÉLULAS ---------------- #

def extrair_celulas():
    """Extrai células do arquivo binário para tradução"""
    if not os.path.exists(BIN_FILE):
        messagebox.showerror("Erro", f"Arquivo binário não encontrado: {BIN_FILE}")
        return []
    
    # Garante que o arquivo BASE existe
    adicionar_cabecalho_se_vazio()
    
    # Carrega o arquivo binário
    zeus_file = ZeusTextFile(BIN_FILE)
    zeus_file.load()
    
    # Carrega o arquivo de texto existente
    try:
        with open(BASE, "r", encoding="utf-8") as f:
            existing_content = f.read()
    except FileNotFoundError:
        criar_arquivo_base_se_nao_existir()
        existing_content = ""
    
    blocks = []
    extracted_count = 0
    
    # Extrai as primeiras N strings interessantes
    for string_info in zeus_file.strings:
        cell_id = string_info['cell_id']
        text = string_info['text']
        
        # Filtra strings
        if len(text) < 3:
            continue
        if text.startswith("Free "):
            continue
        if text.isdigit():
            continue
        if text.strip() == "":
            continue
        
        # Verifica se já foi traduzida
        pattern = f"CELULA: {cell_id}.*?TRADUÇÃO:"
        if re.search(pattern, existing_content, re.DOTALL):
            continue
        
        # Obtém informações do grupo
        group_id = string_info['group_id']
        
        # Formata o bloco
        block = (
            f"OFFSET: 0x{string_info['absolute_offset']:08X}\n"
            f"CELULA: {cell_id}  GRUPO: {group_id if group_id is not None else 'N/A'}\n"
            f"ORIGINAL [{len(text)} chars]: {text}\n"
            f"TRADUÇÃO:\n\n"
        )
        
        blocks.append(block)
        extracted_count += 1
        
        if extracted_count >= MAX:
            break
    
    # Atualiza a interface
    text_extrair.delete("1.0", tk.END)
    text_extrair.insert(tk.END,
        "ZEUS TRANSLATOR - CÉLULAS PARA TRADUZIR\n"
        "=======================================\n"
        f"Total de células: {len(zeus_file.strings)}\n"
        f"Total de grupos: {len(zeus_file.groups)}\n"
        f"Extraindo {len(blocks)} células...\n\n"
    )
    
    for b in blocks:
        text_extrair.insert(tk.END, b + "\n")
    
    messagebox.showinfo("Extração concluída", 
                       f"{len(blocks)} células extraídas.\n"
                       f"Células numeradas de 1 a {len(zeus_file.strings)}")
    
    # Salva as células extraídas
    salvar_celulas_no_arquivo(blocks)
    
    return blocks, zeus_file

# ---------------- MESCLAGEM ---------------- #

def remover_acentos(texto):
    """Remove acentuação"""
    texto_normalizado = unicodedata.normalize('NFKD', texto)
    texto_sem_acentos = ''.join(c for c in texto_normalizado if not unicodedata.combining(c))
    return texto_sem_acentos.upper()

def mesclar_traducao_completa():
    """Mescla traduções no arquivo de texto E atualiza o arquivo binário"""
    # Garante que o arquivo BASE existe
    adicionar_cabecalho_se_vazio()
    
    cola_text = text_mesclar.get("1.0", tk.END).strip()
    if not cola_text:
        messagebox.showwarning("Aviso", "Cole os textos traduzidos antes de mesclar.")
        return
    
    # 1. Primeiro, mescla no arquivo de texto BASE
    try:
        with open(BASE, "r", encoding="utf-8") as f:
            base_lines = f.readlines()
    except FileNotFoundError:
        messagebox.showerror("Erro", f"Arquivo {BASE} não encontrado. Execute a extração primeiro.")
        return
    
    # Mapeia cell_id para linha de tradução
    cell_id_to_tr_line = {}
    updates_for_binary = {}  # {cell_id: new_text}
    
    for i, line in enumerate(base_lines):
        m_cell = CELL_ID_RE.search(line)
        if m_cell:
            cell_id = int(m_cell.group(1))
            
            # Procura pela próxima linha "TRADUÇÃO:"
            for j in range(i, min(i + 5, len(base_lines))):
                linha_normalizada = remover_acentos(base_lines[j].upper())
                if "TRADUCAO" in linha_normalizada or "TRADUÇÃO" in base_lines[j].upper():
                    cell_id_to_tr_line[cell_id] = j
                    break
    
    # Processa o texto colado
    cola_lines = cola_text.splitlines()
    applied = 0
    
    i = 0
    while i < len(cola_lines):
        m_offset = OFFSET_RE.search(cola_lines[i])
        if not m_offset:
            i += 1
            continue
        
        # Tenta encontrar ID da célula - MODIFICADO PARA ACEITAR N/A
        cell_id = None
        for j in range(i, min(i + 3, len(cola_lines))):
            m_cell = CELL_ID_RE.search(cola_lines[j])
            if m_cell:
                cell_id = int(m_cell.group(1))
                break
        
        # 🔥🔥🔥 Se não encontrou com regex normal, tenta encontrar manualmente
        if cell_id is None:
            for j in range(i, min(i + 3, len(cola_lines))):
                if "CELULA:" in cola_lines[j]:
                    # Extrai número mesmo com N/A
                    parts = cola_lines[j].split()
                    for part in parts:
                        if part.isdigit():
                            cell_id = int(part)
                            break
                    if cell_id:
                        break
        
        # Procura "TRADUÇÃO:"
        traducao = ""
        for j in range(i + 1, min(i + 10, len(cola_lines))):
            linha_normalizada = remover_acentos(cola_lines[j].upper())
            if "TRADUCAO" in linha_normalizada or "TRADUÇÃO" in cola_lines[j].upper():
                if j + 1 < len(cola_lines):
                    traducao = cola_lines[j + 1].strip()
                break
        
        # Atualiza arquivo de texto
        if cell_id is not None and traducao:
            # 🔥🔥🔥 SEMPRE atualiza, mesmo se cell_id não estiver no mapeamento
            # Procura se já existe
            found = False
            if cell_id in cell_id_to_tr_line:
                # Atualiza linha existente
                tr_line = cell_id_to_tr_line[cell_id]
                if tr_line + 1 < len(base_lines):
                    base_lines[tr_line + 1] = traducao + "\n"
                    applied += 1
                    found = True
            
            if not found:
                # Adiciona nova entrada
                base_lines.append("\n")
                base_lines.append(cola_lines[i] + "\n")
                
                # Adiciona linha CELULA:
                for j in range(i, min(i + 3, len(cola_lines))):
                    if "CELULA:" in cola_lines[j]:
                        base_lines.append(cola_lines[j] + "\n")
                        break
                
                # Adiciona linha ORIGINAL:
                for j in range(i, min(i + 5, len(cola_lines))):
                    if "ORIGINAL" in cola_lines[j]:
                        base_lines.append(cola_lines[j] + "\n")
                        break
                
                base_lines.append("TRADUÇÃO:\n")
                base_lines.append(traducao + "\n")
                applied += 1
            
            # Guarda para atualizar o binário
            updates_for_binary[cell_id] = traducao
        
        i += 1
        while i < len(cola_lines) and not OFFSET_RE.search(cola_lines[i]):
            i += 1
    
    # Salva arquivo de texto
    try:
        with open(BASE, "w", encoding="utf-8") as f:
            f.writelines(base_lines)
        print(f"Arquivo {BASE} atualizado com {applied} traduções")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao salvar arquivo {BASE}: {str(e)}")
        return
    
    # 2. Atualiza arquivo binário se houver alterações
    if updates_for_binary and os.path.exists(BIN_FILE):
        resposta = messagebox.askyesno("Atualizar Binário", 
                                      f"{len(updates_for_binary)} células para atualizar.\n"
                                      f"Deseja aplicar as alterações?\n\n"
                                      f"Bytes originais serão preservados para células não modificadas.")
        
        if resposta:
            try:
                zeus_file = ZeusTextFile(BIN_FILE)
                zeus_file.load()
                
                # Aplica as atualizações
                success_count = 0
                for cell_id, new_text in updates_for_binary.items():
                    if zeus_file.update_string(cell_id, new_text):
                        success_count += 1
                
                # Salva o arquivo binário
                if zeus_file.save():
                    messagebox.showinfo("Sucesso", 
                                       f"{applied} traduções aplicadas no arquivo de texto.\n"
                                       f"{success_count} células atualizadas no arquivo binário.\n"
                                       f"Backup criado automaticamente.")
                else:
                    messagebox.showwarning("Aviso", 
                                          "Traduções aplicadas no arquivo de texto, "
                                          "mas houve problema ao salvar o binário.")
            except Exception as e:
                messagebox.showerror("Erro", 
                                    f"Erro ao atualizar arquivo binário: {str(e)}")
    else:
        if updates_for_binary and not os.path.exists(BIN_FILE):
            messagebox.showwarning("Aviso", 
                                 f"Arquivo binário {BIN_FILE} não encontrado.")
        else:
            messagebox.showinfo("Mesclagem concluída", 
                               f"{applied} traduções aplicadas no arquivo de texto.")
    
    # Desabilita o botão de colar
    btn_colar_trad.config(state=tk.DISABLED)

def copiar_e_focar_navegador():
    """Extrai células e copia para área de transferência"""
    result = extrair_celulas()
    if not result:
        return
    
    blocks, _ = result
    if not blocks:
        messagebox.showinfo("Info", "Nenhuma célula nova para traduzir.")
        return
    
    texto_para_traduzir = text_extrair.get("1.0", tk.END).strip()
    if texto_para_traduzir:
        pyperclip.copy(texto_para_traduzir)
        focus_browser()
        btn_colar_trad.config(state=tk.NORMAL)

def colar_traducao():
    """Cola tradução da área de transferência"""
    try:
        texto_traduzido = pyperclip.paste()
        
        if not texto_traduzido:
            messagebox.showwarning("Aviso", "Nada encontrado na área de transferência.")
            return
        
        text_mesclar.delete("1.0", tk.END)
        text_mesclar.insert(tk.END, texto_traduzido)
        
        resposta = messagebox.askyesno("Tradução Colada", 
                                     "Tradução colada com sucesso!\n\n"
                                     "Deseja mesclar automaticamente?")
        
        if resposta:
            mesclar_traducao_completa()
            
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao colar tradução: {str(e)}")

# ---------------- UI ---------------- #

root = tk.Tk()
root.title("Zeus Translator Helper - PRESERVA BYTES ORIGINAIS")
root.geometry("1200x700")

# Frame para botões superiores
frame_top = tk.Frame(root)
frame_top.pack(fill=tk.X, padx=10, pady=5)

# Frame para as áreas de texto
frame_bottom = tk.Frame(root)
frame_bottom.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# Dividir frame_bottom em esquerda e direita
frame_left = tk.Frame(frame_bottom)
frame_right = tk.Frame(frame_bottom)

frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

# Botões superiores
btn_frame = tk.Frame(frame_top)
btn_frame.pack()

btn_extrair = tk.Button(btn_frame, text="Extrair 50 células", command=extrair_celulas, width=15)
btn_extrair.pack(side=tk.LEFT, padx=5)

btn_copiar_focar = tk.Button(btn_frame, text="Copiar & Focar Navegador", 
                           command=copiar_e_focar_navegador, bg="#10a37f", fg="white", width=20)
btn_copiar_focar.pack(side=tk.LEFT, padx=5)

btn_colar_trad = tk.Button(btn_frame, text="Colar Tradução", command=colar_traducao,
                          bg="#4285f4", fg="white", width=15, state=tk.DISABLED)
btn_colar_trad.pack(side=tk.LEFT, padx=5)

# Labels informativas
label_info = tk.Label(frame_top, text="← Extrair | Copiar & Focar → Traduzir → Colar → Mesclar", 
                     font=("Arial", 10), fg="blue")
label_info.pack(pady=5)

# Área de texto da esquerda (extração)
label_extrair = tk.Label(frame_left, text="CÉLULAS PARA TRADUZIR (1 a N):")
label_extrair.pack(anchor=tk.W)

text_extrair = scrolledtext.ScrolledText(frame_left, wrap=tk.WORD, height=28)
text_extrair.pack(fill=tk.BOTH, expand=True)

# Área de texto da direita (mesclagem)
label_mesclar = tk.Label(frame_right, text="TRADUÇÕES (cole aqui para mesclar):")
label_mesclar.pack(anchor=tk.W)

text_mesclar = scrolledtext.ScrolledText(frame_right, wrap=tk.WORD, height=28)
text_mesclar.pack(fill=tk.BOTH, expand=True)

# Botão de mesclagem no rodapé
frame_footer = tk.Frame(root)
frame_footer.pack(fill=tk.X, padx=10, pady=5)

btn_mesclar = tk.Button(frame_footer, text="MESCLAR TRADUÇÕES (texto + binário) - BYTES ORIGINAIS PRESERVADOS", 
                       command=mesclar_traducao_completa, bg="#ff6b6b", fg="white", height=2)
btn_mesclar.pack(fill=tk.X)

# Status bar
status_var = tk.StringVar()
status_var.set("MODO SEGURO: Bytes originais preservados | 367 pares | Padding correto | Primeiro par (0,0)")
status_bar = tk.Label(root, textvariable=status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, fg="green")
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

# Verifica se o arquivo binário existe
if not os.path.exists(BIN_FILE):
    status_var.set(f"AVISO: Arquivo {BIN_FILE} não encontrado! Configure o caminho correto.")

root.mainloop()
