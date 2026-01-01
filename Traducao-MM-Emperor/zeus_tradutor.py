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

BASE = "EmperorMM_TRADUZIR.txt"
MAX = 50
BIN_FILE = "EmperorMM.eng"

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
        """Carrega arquivo binário seguindo a estrutura CORRETA"""
        with open(self.filename, 'rb') as f:
            self.data = f.read()
        
        print(f"Tamanho do arquivo: {len(self.data)} bytes")
        
        # 1. File signature (bytes 0-15 / 0x00-0x0F)
        signature = self.data[0:16].decode('ascii', errors='ignore').rstrip('\x00')
        print(f"Assinatura: {signature}")
        
        # 2. Table header (bytes 16-39 / 0x10-0x27) - 6 valores de 4 bytes
        header_offset = 16
        print(f"\nTable header (bytes 0x{header_offset:02X}-0x{header_offset+23:02X}):")
        
        header_values = []
        for i in range(6):  # 6 valores de 4 bytes
            value_offset = header_offset + (i * 4)
            value = struct.unpack('<I', self.data[value_offset:value_offset+4])[0]
            header_values.append(value)
            print(f"  Valor {i}: 0x{value:08X} ({value})")
        
        self.header = {
            'num_count_values': header_values[0],
            'total_cells': header_values[1],
            'mystery_value': header_values[2],
            'reserved': header_values[3],
            'extra1': header_values[4],
            'extra2': header_values[5]
        }
        
        # 3. Table block (bytes 40-80040 / 0x28-0x138A7)
        table_start = 0x28  # 40 decimal
        data_start = 0x138A8  # 80041 decimal
        
        print(f"\nTable block: 0x{table_start:08X} - 0x{data_start-1:08X}")
        print(f"Data block: 0x{data_start:08X} - 0x{len(self.data)-1:08X}")
        
        # Cada linha da table tem 80 bytes (0x50)
        LINE_SIZE = 0x50  # 80 bytes
        
        # Calcula quantas linhas completas existem
        table_size = data_start - table_start
        num_lines = table_size // LINE_SIZE
        
        print(f"\nTable tem {num_lines} linhas de {LINE_SIZE} bytes cada")
        
        self.groups = []  # Vamos chamar de "lines" agora
        line_id = 0
        
        for line_num in range(num_lines):
            line_start = table_start + (line_num * LINE_SIZE)
            line_end = line_start + LINE_SIZE
            
            if line_end > len(self.data):
                break
            
            line_data = self.data[line_start:line_end]
            
            # Extrai os 3 valores de referência (S1, S2, S3)
            # S1: bytes 0x34-0x37 (53-56 decimal) dentro da linha
            # S2: bytes 0x38-0x3B (57-60 decimal)
            # S3: bytes 0x3C-0x3F (61-64 decimal)
            
            s1_offset = 0x34  # Dentro da linha
            s2_offset = 0x38
            s3_offset = 0x3C
            
            s1_value = struct.unpack('<I', line_data[s1_offset:s1_offset+4])[0]
            s2_value = struct.unpack('<I', line_data[s2_offset:s2_offset+4])[0]
            s3_value = struct.unpack('<I', line_data[s3_offset:s3_offset+4])[0]
            
            # Calcula offsets para o Data block
            data_pointers = []
            
            if s1_value != 0:
                data_offset = s1_value - 0x10  # Subtrai 0x10 (16)
                data_pointers.append(('S1', data_offset))
            
            if s2_value != 0:
                data_offset = s2_value - 0x10  # Subtrai 0x10 (16)
                data_pointers.append(('S2', data_offset))
            
            if s3_value != 0:
                data_offset = s3_value - 0x10  # Subtrai 0x10 (16)
                data_pointers.append(('S3', data_offset))
            
            # Salva informações da linha
            line_info = {
                'line_id': line_num,
                'line_start': line_start,
                's1': s1_value,
                's2': s2_value,
                's3': s3_value,
                'data_pointers': data_pointers,  # Lista de (tipo, offset)
                'strings': []  # Células apontadas por esta linha
            }
            
            self.groups.append(line_info)
        
        # 4. Extrai strings do Data block PRESERVANDO CARACTERES ESPECIAIS
        print(f"\n{'='*60}")
        print("EXTRAINDO STRINGS DO DATA BLOCK (PRESERVANDO ESPECIAIS)")
        print(f"{'='*60}")
        
        self.strings = []
        current_offset = 0
        cell_id = 1
        
        data_block = self.data[data_start:]
        
        while current_offset < len(data_block):
            # Encontra próximo null terminator
            end = current_offset
            while end < len(data_block) and data_block[end] != 0:
                end += 1
            
            if end == current_offset:
                # String vazia ou fim do arquivo
                if current_offset == len(data_block) - 1:
                    break  # Último null do arquivo
                string_bytes = b''
                current_offset += 1
            else:
                string_bytes = data_block[current_offset:end]
                current_offset = end + 1
            
            # Ignora strings vazias (apenas null)
            if len(string_bytes) == 0:
                continue
            
            # **CORREÇÃO AQUI**: Preserva bytes exatamente como estão
            # Mas cria uma versão "segura" para exibição
            
            # 1. Salva os bytes originais exatamente
            original_bytes = string_bytes
            
            # 2. Cria uma versão de texto para exibição (substituindo caracteres problemáticos)
            safe_text = ""
            for byte in original_bytes:
                char_code = byte
                # Trata caracteres de controle especiais
                if char_code < 32 and char_code != 9 and char_code != 10 and char_code != 13:  # Não TAB, LF, CR
                    # Caractere de controle - representa como hex
                    safe_text += f"\\x{char_code:02X}"
                elif char_code == 92:  # Backslash
                    safe_text += "\\\\"  # Escapa o backslash
                elif char_code == 10:  # Line feed
                    safe_text += "\\n"
                elif char_code == 13:  # Carriage return
                    safe_text += "\\r"
                elif char_code == 9:   # Tab
                    safe_text += "\\t"
                elif 32 <= char_code <= 126:  # ASCII imprimível
                    safe_text += chr(char_code)
                else:
                    # Tenta decodificar como CP1252, se falhar usa hex
                    try:
                        char = bytes([char_code]).decode('cp1252')
                        safe_text += char
                    except:
                        safe_text += f"\\x{char_code:02X}"
            
            # 3. Para uso interno, mantemos uma versão que pode ser reescrita
            #    Substituindo as sequências \xXX de volta para bytes
            def restore_special_chars(text):
                import re
                # Substitui \xHH por bytes
                def replace_hex(match):
                    hex_str = match.group(1)
                    return chr(int(hex_str, 16))
                
                result = re.sub(r'\\x([0-9A-Fa-f]{2})', replace_hex, text)
                # Substitui escapes comuns
                result = result.replace('\\\\', '\\')
                result = result.replace('\\n', '\n')
                result = result.replace('\\r', '\r')
                result = result.replace('\\t', '\t')
                return result
            
            # Texto restaurado (para quando for salvar)
            restored_text = restore_special_chars(safe_text)
            
            string_info = {
                'cell_id': cell_id,
                'data_offset': current_offset - len(string_bytes) - 1,  # Offset dentro do Data block
                'file_offset': data_start + (current_offset - len(string_bytes) - 1),  # Offset no arquivo
                'original_bytes': original_bytes,
                'safe_text': safe_text,        # Texto com escapes para exibição
                'restored_text': restored_text, # Texto restaurado para salvar
                'modified': False,
                'new_text': None,
                'referenced_by': []  # Quais linhas da table apontam para esta string
            }
            
            self.strings.append(string_info)
            cell_id += 1
            
            # Debug: mostra strings com caracteres especiais
            if cell_id <= 10:
                hex_repr = ' '.join(f'{b:02X}' for b in original_bytes[:20])
                if len(original_bytes) > 20:
                    hex_repr += '...'
                print(f"  Célula {cell_id-1}: offset=0x{string_info['file_offset']:08X}")
                print(f"    Hex: {hex_repr}")
                print(f"    Safe: '{safe_text[:50]}{'...' if len(safe_text) > 50 else ''}'")
        
        print(f"\nStrings extraídas: {len(self.strings)}")
        
        # 5. Mapeia strings para linhas da table
        print(f"\n{'='*60}")
        print("MAPEANDO STRINGS PARA LINHAS DA TABLE")
        print(f"{'='*60}")
        
        # Cria dicionário rápido para busca por file_offset
        strings_by_file_offset = {}
        for s in self.strings:
            strings_by_file_offset[s['file_offset']] = s
        
        total_mapped = 0
        
        for line in self.groups:
            line['strings'] = []
            
            for ptr_type, data_offset in line['data_pointers']:
                file_offset = data_start + data_offset
                
                if file_offset in strings_by_file_offset:
                    string_info = strings_by_file_offset[file_offset]
                    line['strings'].append(string_info['cell_id'])
                    string_info['referenced_by'].append((line['line_id'], ptr_type))
                    total_mapped += 1
        
        # Mostra estatísticas
        print(f"Total de linhas na table: {len(self.groups)}")
        print(f"Total de strings extraídas: {len(self.strings)}")
        print(f"Total de referências mapeadas: {total_mapped}")
        
        # Conta quantas strings únicas foram referenciadas
        unique_referenced = sum(1 for s in self.strings if s['referenced_by'])
        print(f"Strings únicas referenciadas: {unique_referenced}")
        
        # Verifica contra o header
        print(f"\n{'='*60}")
        print("VALIDAÇÃO")
        print(f"{'='*60}")
        
        print(f"Total cells no header: {self.header['total_cells']}")
        print(f"Strings únicas referenciadas: {unique_referenced}")
        
        if unique_referenced == self.header['total_cells']:
            print("✓ CONTAGEM BATE!")
        else:
            print(f"✗ CONTAGEM NÃO BATE! Diferença: {abs(unique_referenced - self.header['total_cells'])}")
        
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
                'group_id': None  # 🔥 INICIALIZA EXPLICITAMENTE COMO None
            })
            
            pos = end_pos + 1
            cell_id += 1
            strings_extracted += 1
        
        print(f"Strings extraídas: {len(self.strings)}")
        
        # Mostra primeiras strings
        print("\nPrimeiras 3 strings:")
        for i in range(min(3, len(self.strings))):
            s = self.strings[i]
            print(f"  Célula {s['cell_id']}: offset={s['offset']}, grupo={s['group_id']}, texto='{s['text']}'")
    
    # 🔥🔥🔥 ADICIONE ESTE MÉTODO SE NÃO EXISTIR 🔥🔥🔥
    def update_string(self, cell_id, new_text):
        """Atualiza uma string pelo ID da célula (1-based) - TRATANDO ESPECIAIS"""
        if 1 <= cell_id <= len(self.strings):
            string_info = self.strings[cell_id - 1]
            string_info['modified'] = True
            
            # **IMPORTANTE**: Precisamos processar sequências especiais como \x0E
            processed_text = self._process_special_sequences(new_text)
            string_info['new_text'] = processed_text
            
            # Log da modificação
            old_len = len(string_info['original_bytes'])
            try:
                new_len = len(processed_text.encode('cp1252'))
            except:
                new_len = len(processed_text.encode('latin-1', errors='replace'))
            
            delta = new_len - old_len
            
            print(f"Célula {cell_id} atualizada:")
            print(f"  Original: '{string_info['safe_text'][:30]}...'")
            print(f"  Novo: '{processed_text[:30]}...'")
            print(f"  Tamanho: {old_len} → {new_len} bytes (Δ={delta})")
            
            return True
        else:
            print(f"ERRO: Célula {cell_id} não encontrada (total: {len(self.strings)} células)")
            return False

    def _process_special_sequences(self, text):
        import re
        
        # Primeiro, escapa barras invertidas duplicadas
        text = text.replace('\\\\', '\\')
        
        # Substitui sequências hexadecimais \xHH
        def replace_hex(match):
            hex_str = match.group(1)
            try:
                return chr(int(hex_str, 16))
            except:
                return match.group(0)  # Mantém como está se inválido
        
        text = re.sub(r'\\x([0-9A-Fa-f]{2})', replace_hex, text)
        
        # Substitui escapes comuns
        text = text.replace('\\n', '\n')
        text = text.replace('\\r', '\r')
        text = text.replace('\\t', '\t')
        
        return text
    
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
        """Salva arquivo binário seguindo a estrutura CORRETA de 4 blocos"""
        print("\n" + "="*60)
        print("SALVANDO ARQUIVO BINÁRIO")
        print("📁 ESTRUTURA: File signature → Table header → Table → Data")
        print("="*60)
        
        # Definições da estrutura
        SIGNATURE_SIZE = 16      # Bytes 0-15 (0x00-0x0F)
        HEADER_SIZE = 24         # Bytes 16-39 (0x10-0x27)
        TABLE_START = 0x28       # Byte 40 (0x28)
        DATA_START = 0x138A8     # Início do Data block (0x138A8)
        LINE_SIZE = 0x50         # Tamanho de cada linha na table (80 bytes)
        
        # 1. Reconstrói Data block com strings modificadas
        print("\n1. Reconstruindo Data block...")
        
        data_block = bytearray()
        string_positions = {}  # Mapeia cell_id → nova posição no data block
        
        current_pos = 0
        
        # Ordena strings por cell_id para manter ordem
        sorted_strings = sorted(self.strings, key=lambda x: x['cell_id'])
        
        for string_info in sorted_strings:
            cell_id = string_info['cell_id']
            
            # Salva a posição desta string no novo data block
            string_positions[cell_id] = current_pos
            
            # Decide qual texto usar (modificado ou original)
            if string_info.get('modified', False) and string_info.get('new_text'):
                text = string_info['new_text']
                try:
                    encoded = text.encode('cp1252')
                except:
                    encoded = text.encode('latin-1', errors='replace')
            else:
                encoded = string_info['original_bytes']
            
            # Adiciona string + null terminator
            data_block.extend(encoded)
            data_block.append(0)
            current_pos += len(encoded) + 1
        
        # Adiciona null final se necessário
        if len(data_block) == 0 or data_block[-1] != 0:
            data_block.append(0)
        
        print(f"   Data block: {len(data_block)} bytes")
        print(f"   Strings processadas: {len(sorted_strings)}")
        
        # 2. Reconstrói Table block
        print("\n2. Reconstruindo Table block...")
        
        table_size = DATA_START - TABLE_START
        num_lines = table_size // LINE_SIZE
        
        print(f"   Tamanho da table: {table_size} bytes")
        print(f"   Número de linhas: {num_lines}")
        
        # Lê a table original para preservar dados não relacionados
        original_table = self.data[TABLE_START:DATA_START]
        
        # Cria nova table
        new_table = bytearray()
        
        # Processa cada linha (80 bytes cada)
        for line_num in range(num_lines):
            line_start = TABLE_START + (line_num * LINE_SIZE)
            line_end = line_start + LINE_SIZE
            
            if line_end > len(self.data):
                break
            
            line_data = self.data[line_start:line_end]
            
            # Prepara nova linha (inicialmente igual à original)
            new_line = bytearray(line_data)
            
            # Atualiza S1, S2, S3 se necessário
            # Posições dentro da linha: S1=0x34, S2=0x38, S3=0x3C
            
            # Para cada ponteiro (S1, S2, S3)
            for ptr_offset, ptr_name in [(0x34, 'S1'), (0x38, 'S2'), (0x3C, 'S3')]:
                # Lê valor original
                original_value = struct.unpack('<I', line_data[ptr_offset:ptr_offset+4])[0]
                
                # Se tem valor não-zero, precisa recalcular
                if original_value != 0:
                    # Calcula offset no data block original
                    original_data_offset = original_value - 0x10
                    original_file_offset = DATA_START + original_data_offset
                    
                    # Encontra qual string estava neste offset
                    target_string = None
                    for s in self.strings:
                        if s.get('file_offset') == original_file_offset:
                            target_string = s
                            break
                    
                    # Se encontrou a string, calcula novo offset
                    if target_string:
                        cell_id = target_string['cell_id']
                        
                        if cell_id in string_positions:
                            new_data_offset = string_positions[cell_id]
                            new_value = new_data_offset + 0x10  # Adiciona 0x10
                            
                            # Atualiza na nova linha
                            new_line[ptr_offset:ptr_offset+4] = struct.pack('<I', new_value)
                            
                            # Debug para primeiras linhas
                            if line_num < 5:
                                print(f"   Linha {line_num} {ptr_name}: "
                                      f"0x{original_value:08X}→0x{new_value:08X} "
                                      f"(célula {cell_id})")
            
            # Adiciona linha à nova table
            new_table.extend(new_line)
        
        # Garante que a table tenha o tamanho correto
        if len(new_table) < table_size:
            padding = table_size - len(new_table)
            new_table.extend(b'\x00' * padding)
            print(f"   Padding adicionado: {padding} bytes")
        
        print(f"   Table reconstruída: {len(new_table)} bytes")
        
        # 3. Reconstrói Header (preserva valores originais)
        print("\n3. Preparando Header...")
        
        # Mantém os 6 valores originais do header
        header_values = []
        for i in range(6):
            offset = 16 + (i * 4)
            value = struct.unpack('<I', self.data[offset:offset+4])[0]
            header_values.append(value)
        
        # Cria header block
        header_block = bytearray()
        for value in header_values:
            header_block.extend(struct.pack('<I', value))
        
        print(f"   Header: {len(header_block)} bytes")
        print(f"   Valores: {[f'0x{v:08X}' for v in header_values]}")
        
        # 4. Reconstrói Signature
        signature_block = bytearray()
        signature = b'Emperor MM file.'
        signature_block.extend(signature.ljust(16, b'\x00'))
        
        # 5. Monta arquivo completo
        print("\n4. Montando arquivo completo...")
        
        new_data = bytearray()
        
        # File signature (0x00-0x0F)
        new_data.extend(signature_block)
        
        # Table header (0x10-0x27)
        new_data.extend(header_block)
        
        # Table (0x28-0x138A7)
        new_data.extend(new_table)
        
        # Data (0x138A8-end)
        new_data.extend(data_block)
        
        print(f"\n   Tamanhos dos blocos:")
        print(f"     Signature: {len(signature_block)} bytes")
        print(f"     Header: {len(header_block)} bytes")
        print(f"     Table: {len(new_table)} bytes")
        print(f"     Data: {len(data_block)} bytes")
        print(f"     Total: {len(new_data)} bytes")
        
        # 6. Validação
        print("\n5. Validação...")
        
        # Verifica estrutura básica
        if len(new_data) < DATA_START:
            print(f"✗ ERRO: Arquivo muito pequeno para a estrutura!")
            return False
        
        # Verifica assinatura
        new_signature = new_data[0:16].decode('ascii', errors='ignore').rstrip('\x00')
        if new_signature != "Emperor MM file.":
            print(f"✗ ERRO: Assinatura incorreta: {new_signature}")
            return False
        
        print(f"   ✓ Assinatura: {new_signature}")
        
        # 7. Salva arquivo
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{self.filename}.backup_{timestamp}"
        
        try:
            # Backup do original
            with open(backup_name, 'wb') as f:
                f.write(self.data)
            print(f"\n✓ Backup criado: {backup_name}")
            
            # Novo arquivo
            with open(self.filename, 'wb') as f:
                f.write(new_data)
            
            print(f"✓ Arquivo salvo: {self.filename}")
            print(f"  Tamanho original: {len(self.data)} bytes")
            print(f"  Tamanho novo: {len(new_data)} bytes")
            
            # Atualiza dados internos
            self.data = new_data
            
            # Verificação final
            print(f"\n✓ Estrutura preservada: 4 blocos")
            print(f"✓ Total de strings: {len(self.strings)}")
            print(f"✓ Strings modificadas: {sum(1 for s in self.strings if s.get('modified', False))}")
            
            return True
            
        except Exception as e:
            print(f"\n✗ ERRO ao salvar: {e}")
            import traceback
            traceback.print_exc()
            return False

    def find_cell_by_original_offset(self, original_offset):
        """Encontra a célula que começa exatamente nesse offset original"""
        if not hasattr(self, 'strings') or not self.strings:
            return None
        
        for s in self.strings:
            if s.get('offset', -1) == original_offset:
                return s.get('cell_id', None)
        return None

    def verify_saved_file(self, new_data):
        """Verifica se o arquivo foi salvo corretamente com a nova estrutura"""
        print("\n" + "="*60)
        print("VERIFICAÇÃO DO ARQUIVO SALVO")
        print("ESTRUTURA: 4 blocos")
        print("="*60)
        
        try:
            # 1. File signature (0x00-0x0F)
            if len(new_data) < 16:
                print(f"✗ Arquivo muito pequeno: {len(new_data)} bytes")
                return False
                
            signature = new_data[0:16].decode('ascii', errors='ignore').rstrip('\x00')
            print(f"1. File signature: {signature}")
            
            # 2. Table header (0x10-0x27)
            if len(new_data) < 40:
                print(f"✗ Arquivo muito pequeno para header: {len(new_data)} bytes")
                return False
                
            num_count = struct.unpack('<I', new_data[16:20])[0]
            total_cells = struct.unpack('<I', new_data[20:24])[0]
            print(f"2. Table header:")
            print(f"   num_count_values: {num_count}")
            print(f"   total_cells: {total_cells}")
            
            # Verifica se os valores são válidos
            if num_count < 0 or num_count > 4294967295:
                print(f"   ⚠️ num_count_values fora do range: {num_count}")
            
            if total_cells < 0 or total_cells > 4294967295:
                print(f"   ⚠️ total_cells fora do range: {total_cells}")
            
            # 3. Table block (0x28-0x138A7)
            print(f"3. Table block (primeiros 3 pares):")
            
            if len(new_data) < 64:
                print(f"✗ Arquivo muito pequeno para table: {len(new_data)} bytes")
                return False
            
            # Par 0
            count0 = struct.unpack('<I', new_data[40:44])[0]    # COUNT
            offset0 = struct.unpack('<I', new_data[44:48])[0]   # OFFSET
            print(f"   Par 0: count={count0}, offset=0x{offset0:04X}")
            
            # Par 1
            count1 = struct.unpack('<I', new_data[48:52])[0]    # COUNT
            offset1 = struct.unpack('<I', new_data[52:56])[0]   # OFFSET
            print(f"   Par 1: count={count1}, offset=0x{offset1:04X}")
            
            # Par 2
            count2 = struct.unpack('<I', new_data[56:60])[0]    # COUNT
            offset2 = struct.unpack('<I', new_data[60:64])[0]   # OFFSET
            print(f"   Par 2: count={count2}, offset=0x{offset2:04X}")
            
            # 4. Data block (0x138A8)
            data_start = 0x138A8
            print(f"4. Data block começa em: 0x{data_start:08X}")
            
            if len(new_data) > data_start:
                print(f"   Tamanho do Data block: {len(new_data) - data_start} bytes")
                
                # Verifica alguns bytes do início do Data block
                if len(new_data) > data_start + 16:
                    first_data = new_data[data_start:data_start+16]
                    hex_str = ' '.join(f'{b:02X}' for b in first_data)
                    print(f"   Primeiros bytes do Data: {hex_str}")
            else:
                print(f"   ⚠️ Data block vazio ou inexistente")
            
            print(f"\n✓ Arquivo verificado com sucesso!")
            print(f"✓ Estrutura correta: 4 blocos")
            print(f"✓ Tamanho total: {len(new_data)} bytes")
            
            return True
            
        except struct.error as e:
            print(f"\n✗ ERRO de struct na verificação: {e}")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"\n✗ ERRO na verificação: {e}")
            import traceback
            traceback.print_exc()
            return False

# ---------------- FUNÇÕES AUXILIARES ---------------- #

def criar_arquivo_base_se_nao_existir():
    """Cria o arquivo BASE se ele não existir"""
    if not os.path.exists(BASE):
        with open(BASE, "w", encoding="utf-8") as f:
            f.write(f"# Arquivo de tradução Zeus Text\n")
            f.write(f"# Criado em: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Formato:\n")
            f.write(f"# OFFSET: 0xXXXXXXX\n")
            f.write(f"# CELULA: X  GRUPO: Y\n")
            f.write(f"# ORIGINAL [N chars]: texto original\n")
            f.write(f"# TRADUÇÃO:\n")
            f.write(f"# texto traduzido\n\n")
        print(f"Arquivo {BASE} criado com sucesso!")
        return True
    return False

def extrair_todas_as_celulas():
    """Extrai TODAS as células do arquivo binário para o arquivo BASE de uma vez"""
    if not os.path.exists(BIN_FILE):
        messagebox.showerror("Erro", f"Arquivo binário não encontrado: {BIN_FILE}")
        return None
    
    print("\n" + "="*60)
    print("EXTRAINDO TODAS AS CÉLULAS")
    print("="*60)
    
    # Carrega o arquivo binário
    zeus_file = ZeusTextFile(BIN_FILE)
    zeus_file.load()
    
    # Verifica se já existe um arquivo com extração completa
    criar_arquivo_base_se_nao_existir()
    
    # Lê o conteúdo atual do arquivo
    try:
        with open(BASE, "r", encoding="utf-8") as f:
            existing_content = f.read()
    except FileNotFoundError:
        existing_content = ""
    
    # Extrai IDs de células já existentes
    existing_cell_ids = set()
    for match in re.finditer(r"CELULA:\s*(\d+)", existing_content):
        existing_cell_ids.add(int(match.group(1)))
    
    total_cells = len(zeus_file.strings)
    
    print(f"Células no arquivo binário: {total_cells}")
    print(f"Células já no arquivo .txt: {len(existing_cell_ids)}")
    
    # Prepara para extrair células que faltam
    cells_to_extract = []
    
    for string_info in zeus_file.strings:
        cell_id = string_info['cell_id']
        
        # Se a célula não existe no arquivo, extrai
        if cell_id not in existing_cell_ids:
            cells_to_extract.append(string_info)
    
    print(f"Células para extrair: {len(cells_to_extract)}")
    
    # Extrai todas as células que faltam
    blocks = []
    for string_info in cells_to_extract:
        cell_id = string_info['cell_id']
        text = string_info['safe_text']
        
        # CORREÇÃO: Usa as chaves corretas da nova estrutura
        # offset = string_info.get('file_offset', string_info.get('absolute_offset', 0))
        offset = string_info.get('file_offset', 0)
        
        # Obtém informações de referência
        referenced_by = string_info.get('referenced_by', [])
        ref_info = ""
        
        if referenced_by:
            # Pega todas as referências
            ref_list = []
            for line_id, ptr_type in referenced_by:
                ref_list.append(f"L{line_id}[{ptr_type}]")
            ref_info = f"  REFERÊNCIAS: {', '.join(ref_list)}"
        
        # Formata o bloco COMPLETO
        block = (
            f"OFFSET: 0x{offset:08X}\n"
            f"CELULA: {cell_id}{ref_info}\n"
            f"ORIGINAL [{len(text)} chars]: {text}\n"
            f"TRADUÇÃO:\n\n"
        )
        
        blocks.append(block)
    
    # Se houver novas células, adiciona ao arquivo
    if blocks:
        try:
            with open(BASE, "a", encoding="utf-8") as f:
                for block in blocks:
                    f.write(block)
            
            print(f"Adicionadas {len(blocks)} novas células ao arquivo {BASE}")
            
            # Atualiza a interface
            text_extrair.delete("1.0", tk.END)
            text_extrair.insert(tk.END,
                "ZEUS TRANSLATOR - TODAS AS CÉLULAS\n"
                "==================================\n"
                f"Arquivo: {BIN_FILE}\n"
                f"Total de células no binário: {total_cells}\n"
                f"Células já no arquivo .txt: {len(existing_cell_ids)}\n"
                f"Células adicionadas agora: {len(blocks)}\n"
                f"\nO arquivo {BASE} agora contém TODAS as células.\n"
                f"Você pode traduzir em qualquer ordem.\n\n"
                f"Status: {len(blocks)} novas células adicionadas\n"
                f"Total no arquivo: {len(existing_cell_ids) + len(blocks)} células\n"
            )
            
            messagebox.showinfo("Extração Completa", 
                              f"Extraição concluída!\n\n"
                              f"Total de células no binário: {total_cells}\n"
                              f"Células já no arquivo: {len(existing_cell_ids)}\n"
                              f"Células adicionadas: {len(blocks)}\n\n"
                              f"O arquivo {BASE} agora contém TODAS as células.")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar células: {str(e)}")
    else:
        # Atualiza a interface mesmo se não houver novas células
        text_extrair.delete("1.0", tk.END)
        text_extrair.insert(tk.END,
            "ZEUS TRANSLATOR - TODAS AS CÉLULAS\n"
            "==================================\n"
            f"Arquivo: {BIN_FILE}\n"
            f"Total de células no binário: {total_cells}\n"
            f"Células já no arquivo .txt: {len(existing_cell_ids)}\n"
            f"\nTodas as células já estão no arquivo {BASE}\n"
            f"Continue traduzindo e use 'Mesclar' para atualizar.\n\n"
            f"Status: Nenhuma célula nova adicionada\n"
            f"Total no arquivo: {len(existing_cell_ids)} células\n"
        )
        
        messagebox.showinfo("Extração Completa", 
                          f"Todas as {total_cells} células já estão no arquivo.\n"
                          f"Use 'Extrair para traduzir' para pegar células não traduzidas.")
    
    return zeus_file

def extrair_celulas_para_traducao():
    """Extrai um lote de células para tradução (apenas as não traduzidas)"""
    if not os.path.exists(BASE):
        messagebox.showinfo("Info", "Execute 'Extrair TODAS as células' primeiro.")
        return None
    
    try:
        with open(BASE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        messagebox.showinfo("Info", "Execute 'Extrair TODAS as células' primeiro.")
        return None
    
    print("\n" + "="*60)
    print("ANALISANDO CÉLULAS PARA TRADUÇÃO")
    print("="*60)
    
    # Divide o conteúdo em blocos por célula
    blocks = content.split("\n\n")
    
    # Encontra todos os blocos que começam com OFFSET:
    cell_blocks = []
    for block in blocks:
        if block.strip().startswith("OFFSET:"):
            cell_blocks.append(block.strip())
    
    print(f"Total de blocos encontrados: {len(cell_blocks)}")
    
    # Analisa cada bloco para verificar se tem tradução
    untranslated_blocks = []
    translated_count = 0
    
    for block in cell_blocks:
        lines = block.split('\n')
        if len(lines) < 4:
            continue
        
        # Extrai cell_id
        cell_id = None
        for line in lines:
            if line.startswith("CELULA:"):
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        cell_id = int(part)
                        break
                break
        
        if cell_id is None:
            continue
        
        # Verifica se tem tradução
        has_translation = False
        found_traducao_line = False
        
        for i, line in enumerate(lines):
            if "TRADUÇÃO:" in line:
                found_traducao_line = True
                # Verifica se a próxima linha tem conteúdo
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and next_line != "" and not next_line.startswith("OFFSET:"):
                        has_translation = True
                        translated_count += 1
                break
        
        if not has_translation:
            untranslated_blocks.append((cell_id, block))
    
    print(f"Total de células: {len(cell_blocks)}")
    print(f"Células traduzidas: {translated_count}")
    print(f"Células não traduzidas: {len(untranslated_blocks)}")
    
    # Ordena por cell_id
    untranslated_blocks.sort(key=lambda x: x[0])
    
    # Limita ao máximo
    selected_blocks = untranslated_blocks[:MAX]
    
    # Prepara texto para tradução
    output_text = ""
    for cell_id, block in selected_blocks:
        output_text += block + "\n\n"
    
    # Atualiza a interface
    text_extrair.delete("1.0", tk.END)
    text_extrair.insert(tk.END,
        "ZEUS TRANSLATOR - CÉLULAS PARA TRADUZIR\n"
        "=======================================\n"
        f"Total de células no arquivo: {len(cell_blocks)}\n"
        f"Células traduzidas: {translated_count}\n"
        f"Células não traduzidas: {len(untranslated_blocks)}\n"
        f"Extraindo {len(selected_blocks)} células para tradução...\n\n"
    )
    
    text_extrair.insert(tk.END, output_text)
    
    if selected_blocks:
        messagebox.showinfo("Extração concluída", 
                          f"{len(selected_blocks)} células não traduzidas extraídas.\n"
                          f"Total de células: {len(cell_blocks)}\n"
                          f"Traduzidas: {translated_count}\n"
                          f"Restantes: {len(untranslated_blocks)}")
    else:
        messagebox.showinfo("Tradução Concluída", 
                          "Todas as células já foram traduzidas!\n"
                          f"Total: {len(cell_blocks)} células")
    
    return selected_blocks

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

# ---------------- MESCLAGEM ---------------- #

def remover_acentos(texto):
    """Remove acentuação"""
    texto_normalizado = unicodedata.normalize('NFKD', texto)
    texto_sem_acentos = ''.join(c for c in texto_normalizado if not unicodedata.combining(c))
    return texto_sem_acentos.upper()

def mesclar_traducao_completa():
    """Mescla traduções no arquivo de texto E atualiza o arquivo binário COM VALIDAÇÃO"""
    # Garante que o arquivo BASE existe
    criar_arquivo_base_se_nao_existir()
    
    cola_text = text_mesclar.get("1.0", tk.END).strip()
    if not cola_text:
        messagebox.showwarning("Aviso", "Cole os textos traduzidos antes de mesclar.")
        return
    
    # 1. Primeiro, mescla no arquivo de texto BASE
    try:
        with open(BASE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        messagebox.showerror("Erro", f"Arquivo {BASE} não encontrado. Execute a extração primeiro.")
        return
    
    # Processa o texto colado linha por linha
    cola_lines = cola_text.splitlines()
    applied = 0
    validation_errors = []  # Lista de erros de validação
    updates_for_binary = {}  # {cell_id: new_text}
    validated_cells = []    # Células que passaram na validação
    
    i = 0
    while i < len(cola_lines):
        # Procura por linha OFFSET:
        if cola_lines[i].startswith("OFFSET:"):
            # Encontra o início do bloco
            start_idx = i
            
            # Procura o cell_id neste bloco
            cell_id = None
            offset_line = cola_lines[i]
            original_text_from_clipboard = None
            original_length_from_clipboard = None
            
            # Procura nas próximas linhas pelo cell_id e texto original
            for j in range(start_idx, min(start_idx + 5, len(cola_lines))):
                line = cola_lines[j]
                
                # Extrai cell_id
                if "CELULA:" in line:
                    parts = line.split()
                    for part in parts:
                        if part.isdigit():
                            cell_id = int(part)
                            break
                
                # Extrai texto original
                if "ORIGINAL [" in line and "chars]:" in line:
                    # Extrai o texto original do clipboard
                    try:
                        # Formato: ORIGINAL [N chars]: texto
                        match = ORIG_RE.match(line)
                        if match:
                            original_length_from_clipboard = int(match.group(1))
                            original_text_from_clipboard = match.group(2)
                    except:
                        pass
                    
                if cell_id and original_text_from_clipboard:
                    break
            
            # Procura pela tradução
            traducao = ""
            for j in range(start_idx, min(start_idx + 10, len(cola_lines))):
                if "TRADUÇÃO:" in cola_lines[j]:
                    # A tradução deve estar na próxima linha
                    if j + 1 < len(cola_lines):
                        traducao = cola_lines[j + 1].strip()
                    break
            
            # Se encontrou cell_id e tradução, VALIDA antes de atualizar
            if cell_id is not None and traducao and original_text_from_clipboard:
                print(f"\nProcessando célula {cell_id}:")
                print(f"  Original no clipboard: '{original_text_from_clipboard}'")
                print(f"  Tradução: '{traducao}'")
                
                # VALIDAÇÃO: Verifica no arquivo BASE se o original bate
                validation_passed = True
                error_msg = ""
                
                # Encontra o bloco desta célula no conteúdo do arquivo BASE
                block_start = content.find(f"CELULA: {cell_id} ")
                if block_start != -1:
                    # Volta para encontrar OFFSET:
                    offset_start = content.rfind("OFFSET:", 0, block_start)
                    if offset_start != -1:
                        block_end = content.find("\n\n", offset_start)
                        if block_end == -1:
                            block_end = len(content)
                        
                        block = content[offset_start:block_end]
                        
                        # Extrai texto original do arquivo BASE
                        file_original_text = None
                        file_original_length = None
                        
                        lines = block.split('\n')
                        for line in lines:
                            if "ORIGINAL [" in line and "chars]:" in line:
                                try:
                                    match = ORIG_RE.match(line)
                                    if match:
                                        file_original_length = int(match.group(1))
                                        file_original_text = match.group(2)
                                        break
                                except:
                                    pass
                        
                        if file_original_text:
                            print(f"  Original no arquivo: '{file_original_text}'")
                            
                            # Compara os textos originais
                            if file_original_text != original_text_from_clipboard:
                                validation_passed = False
                                error_msg = f"Célula {cell_id}: Texto original não corresponde!\n" \
                                          f"Arquivo: '{file_original_text}'\n" \
                                          f"Clipboard: '{original_text_from_clipboard}'"
                                
                                # Verifica se a diferença é apenas em espaços ou formatação
                                if file_original_text.strip() == original_text_from_clipboard.strip():
                                    print(f"  Aviso: Diferença apenas em espaços, corrigindo...")
                                    # Atualiza o texto no clipboard para bater com o arquivo
                                    original_text_from_clipboard = file_original_text
                                    validation_passed = True
                                    error_msg = ""
                                    print(f"  ✓ Corrigido: '{file_original_text}'")
                        else:
                            validation_passed = False
                            error_msg = f"Célula {cell_id}: Não encontrou texto original no arquivo!"
                else:
                    validation_passed = False
                    error_msg = f"Célula {cell_id}: Não encontrada no arquivo {BASE}!"
                
                # Se validação falhou
                if not validation_passed:
                    print(f"  ✗ VALIDAÇÃO FALHOU: {error_msg}")
                    validation_errors.append(f"Célula {cell_id}: {error_msg}")
                    
                    # Adiciona marcador de erro na interface
                    current_text = text_extrair.get("1.0", tk.END)
                    if f"Célula {cell_id}:" not in current_text:
                        error_marker = f"\n\n⚠️ ERRO VALIDAÇÃO CÉLULA {cell_id}:\n" \
                                      f"Texto original não corresponde!\n"
                        text_extrair.insert(tk.END, error_marker)
                    
                    i += 1
                    continue
                
                print(f"  ✓ Validação OK")
                validated_cells.append(cell_id)
                
                # Procura o bloco completo no conteúdo para atualização
                block_start = content.find(f"OFFSET:")
                found_block = False
                
                while block_start != -1 and not found_block:
                    block_end = content.find("\n\n", block_start)
                    if block_end == -1:
                        block_end = len(content)
                    
                    block = content[block_start:block_end]
                    
                    # Verifica se é a célula certa
                    if f"CELULA: {cell_id}" in block and "TRADUÇÃO:" in block:
                        # Divide o bloco em linhas
                        lines = block.split('\n')
                        new_block_lines = []
                        traducao_encontrada = False
                        skip_next_line = False
                        
                        for k, line in enumerate(lines):
                            # Se esta é a linha TRADUÇÃO:, a mantemos
                            if "TRADUÇÃO:" in line:
                                new_block_lines.append(line)
                                traducao_encontrada = True
                                
                                # Verifica se já existe uma tradução na próxima linha
                                if k + 1 < len(lines):
                                    next_line = lines[k + 1].strip()
                                    # Se a próxima linha não é vazia e não começa com OFFSET:, CELULA: ou ORIGINAL
                                    if (next_line and 
                                        not next_line.startswith("OFFSET:") and 
                                        not next_line.startswith("CELULA:") and 
                                        not "ORIGINAL [" in next_line and
                                        not "TRADUÇÃO:" in next_line):
                                        # Esta linha já tem uma tradução existente, vamos substituí-la
                                        print(f"  → Substituindo tradução existente: '{next_line}' por '{traducao}'")
                                        # Não adicionamos a linha existente, apenas a nova tradução
                                        new_block_lines.append(traducao)
                                        skip_next_line = True  # Marca para pular a próxima linha
                                    else:
                                        # Não tem tradução existente, adiciona a nova
                                        print(f"  → Adicionando nova tradução: '{traducao}'")
                                        new_block_lines.append(traducao)
                                else:
                                    # Última linha, adiciona a tradução
                                    print(f"  → Adicionando nova tradução: '{traducao}'")
                                    new_block_lines.append(traducao)
                            elif skip_next_line:
                                # Pula a linha que era a tradução antiga
                                skip_next_line = False
                                print(f"  → Removendo tradução antiga: '{line}'")
                            else:
                                # Mantém outras linhas
                                new_block_lines.append(line)
                        
                        # Se não encontrou linha TRADUÇÃO: (caso raro), adiciona
                        if not traducao_encontrada:
                            print(f"  → Adicionando linha TRADUÇÃO: faltante")
                            # Encontra onde adicionar (após ORIGINAL)
                            for k, line in enumerate(new_block_lines):
                                if "ORIGINAL [" in line:
                                    # Adiciona TRADUÇÃO: e a tradução depois desta linha
                                    new_block_lines.insert(k + 1, "TRADUÇÃO:")
                                    new_block_lines.insert(k + 2, traducao)
                                    break
                        
                        new_block = '\n'.join(new_block_lines)
                        
                        # Substitui no conteúdo
                        content = content[:block_start] + new_block + content[block_end:]
                        applied += 1
                        updates_for_binary[cell_id] = traducao
                        print(f"  → Célula {cell_id} atualizada no arquivo")
                        found_block = True
                        break
                    
                    block_start = content.find("OFFSET:", block_end)
        
        i += 1
    
    # Mostra resumo na interface
    text_extrair.insert(tk.END, f"\n\n{'='*50}\n")
    text_extrair.insert(tk.END, f"RESUMO DA MESCLAGEM:\n")
    text_extrair.insert(tk.END, f"Células validadas: {len(validated_cells)}\n")
    text_extrair.insert(tk.END, f"Células com erro: {len(validation_errors)}\n")
    
    # Mostra erros de validação se houver
    if validation_errors:
        error_window = tk.Toplevel(root)
        error_window.title("Erros de Validação - Texto Original Não Corresponde")
        error_window.geometry("700x500")
        
        # Frame principal
        main_frame = tk.Frame(error_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Label explicativa
        label = tk.Label(main_frame, text="As seguintes células NÃO serão mescladas:", 
                        font=("Arial", 10, "bold"), fg="red")
        label.pack(anchor=tk.W, pady=(0, 10))
        
        # Área de texto com scroll
        error_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15)
        error_text.pack(fill=tk.BOTH, expand=True)
        
        error_content = f"ERROS DE VALIDAÇÃO ENCONTRADOS ({len(validation_errors)} células):\n"
        error_content += "=" * 60 + "\n\n"
        
        for error in validation_errors:
            error_content += error + "\n" + "-" * 40 + "\n"
        
        error_text.insert(tk.END, error_content)
        error_text.config(state=tk.DISABLED)  # Somente leitura
        
        # Frame para botões
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        # Botão para continuar apenas com células válidas
        def continue_valid_only():
            error_window.destroy()
            save_and_update(applied, content, updates_for_binary, validation_errors)
        
        # Botão para cancelar
        def cancel_merge():
            error_window.destroy()
            messagebox.showinfo("Cancelado", "Mesclagem cancelada devido a erros de validação.")
            return
        
        btn_continue = tk.Button(btn_frame, text="Continuar (Apenas células válidas)", 
                                command=continue_valid_only, bg="#4CAF50", fg="white")
        btn_continue.pack(side=tk.LEFT, padx=5)
        
        btn_cancel = tk.Button(btn_frame, text="Cancelar Mesclagem", 
                              command=cancel_merge, bg="#f44336", fg="white")
        btn_cancel.pack(side=tk.LEFT, padx=5)
        
    else:
        # Nenhum erro, continua normalmente
        save_and_update(applied, content, updates_for_binary, validation_errors)

def save_and_update(applied, content, updates_for_binary, validation_errors):
    """Salva arquivo e atualiza binário (função auxiliar)"""
    # Salva arquivo de texto se houve alterações
    if applied > 0:
        try:
            with open(BASE, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ Arquivo {BASE} atualizado com {applied} traduções")
            
            # Atualiza interface
            text_extrair.insert(tk.END, f"\n✓ {applied} traduções aplicadas no arquivo de texto\n")
            
            # Mostra exemplo de célula atualizada (para debug)
            if updates_for_binary:
                first_cell = next(iter(updates_for_binary))
                # Encontra este bloco no conteúdo salvo
                start_idx = content.find(f"CELULA: {first_cell} ")
                if start_idx != -1:
                    offset_start = content.rfind("OFFSET:", 0, start_idx)
                    if offset_start != -1:
                        block_end = content.find("\n\n", offset_start)
                        if block_end != -1:
                            block = content[offset_start:block_end]
                            # Encontra a linha da tradução
                            for line in block.split('\n'):
                                if "TRADUÇÃO:" in line:
                                    trad_idx = block.find(line)
                                    if trad_idx != -1:
                                        trad_line_start = trad_idx + len(line) + 1
                                        trad_line_end = block.find('\n', trad_line_start)
                                        if trad_line_end == -1:
                                            trad_line_end = len(block)
                                        trad_text = block[trad_line_start:trad_line_end].strip()
                                        print(f"  Exemplo célula {first_cell}: TRADUÇÃO: '{trad_text}'")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar arquivo {BASE}: {str(e)}")
            return
    
    # 2. Atualiza arquivo binário se houver alterações
    if updates_for_binary and os.path.exists(BIN_FILE):
        resposta = messagebox.askyesno("Atualizar Binário", 
                                      f"{len(updates_for_binary)} células validadas para atualizar.\n"
                                      f"{len(validation_errors)} células ignoradas (erro de validação).\n\n"
                                      f"Deseja aplicar as alterações válidas?")
        
        if resposta:
            try:
                zeus_file = ZeusTextFile(BIN_FILE)
                zeus_file.load()
                
                # Aplica as atualizações apenas das células validadas
                success_count = 0
                error_count = 0
                
                for cell_id, new_text in updates_for_binary.items():
                    try:
                        if zeus_file.update_string(cell_id, new_text):
                            success_count += 1
                            print(f"✓ Célula {cell_id} atualizada no binário")
                        else:
                            error_count += 1
                            print(f"✗ Erro ao atualizar célula {cell_id} no binário")
                    except Exception as e:
                        error_count += 1
                        print(f"✗ Exceção ao atualizar célula {cell_id}: {e}")
                
                # Salva o arquivo binário
                if zeus_file.save():
                    messagebox.showinfo("Sucesso", 
                                       f"{applied} traduções aplicadas no arquivo de texto.\n"
                                       f"{success_count} células atualizadas no arquivo binário.\n"
                                       f"{error_count} erros ao atualizar binário.\n"
                                       f"{len(validation_errors)} células ignoradas (validação).\n"
                                       f"Backup criado automaticamente.")
                    
                    # Atualiza interface
                    text_extrair.insert(tk.END, f"✓ {success_count} células atualizadas no binário\n")
                    if error_count > 0:
                        text_extrair.insert(tk.END, f"⚠️ {error_count} erros ao atualizar binário\n")
                    if len(validation_errors) > 0:
                        text_extrair.insert(tk.END, f"✗ {len(validation_errors)} células ignoradas (validação)\n")
                    
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
            text_extrair.insert(tk.END, f"⚠️ Arquivo binário {BIN_FILE} não encontrado\n")
        elif applied > 0:
            if validation_errors:
                messagebox.showinfo("Mesclagem Parcial", 
                                   f"{applied} traduções aplicadas no arquivo de texto.\n"
                                   f"{len(validation_errors)} células ignoradas (erro de validação).")
                text_extrair.insert(tk.END, f"⚠️ {len(validation_errors)} células ignoradas (validação)\n")
            else:
                messagebox.showinfo("Mesclagem concluída", 
                                   f"{applied} traduções aplicadas no arquivo de texto.")
                text_extrair.insert(tk.END, f"✓ Mesclagem concluída com sucesso!\n")
        else:
            messagebox.showwarning("Aviso", 
                                 "Nenhuma tradução aplicada. Verifique o formato.")
            text_extrair.insert(tk.END, f"✗ Nenhuma tradução aplicada\n")
    
    # Desabilita o botão de colar
    btn_colar_trad.config(state=tk.DISABLED)

def copiar_e_focar_navegador():
    """Extrai células NÃO TRADUZIDAS e copia para área de transferência"""
    blocks = extrair_celulas_para_traducao()
    
    if not blocks:
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
root.title("Zeus Translator Helper - EXTRATOR COMPLETO")
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

btn_extrair_todas = tk.Button(btn_frame, text="Extrair TODAS as células", 
                            command=extrair_todas_as_celulas, bg="#4CAF50", fg="white", width=20)
btn_extrair_todas.pack(side=tk.LEFT, padx=5)

btn_extrair_lote = tk.Button(btn_frame, text="Extrair para traduzir", 
                           command=extrair_celulas_para_traducao, width=20)
btn_extrair_lote.pack(side=tk.LEFT, padx=5)

btn_copiar_focar = tk.Button(btn_frame, text="Copiar & Focar Navegador", 
                           command=copiar_e_focar_navegador, bg="#10a37f", fg="white", width=20)
btn_copiar_focar.pack(side=tk.LEFT, padx=5)

btn_colar_trad = tk.Button(btn_frame, text="Colar Tradução", command=colar_traducao,
                          bg="#4285f4", fg="white", width=15, state=tk.DISABLED)
btn_colar_trad.pack(side=tk.LEFT, padx=5)

# Labels informativas
label_info = tk.Label(frame_top, text="Extrair TODAS → Extrair para traduzir → Copiar → Traduzir → Colar → Mesclar", 
                     font=("Arial", 10), fg="blue")
label_info.pack(pady=5)

# Área de texto da esquerda (extração)
label_extrair = tk.Label(frame_left, text="CÉLULAS PARA TRADUZIR:")
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

btn_mesclar = tk.Button(frame_footer, text="MESCLAR TRADUÇÕES (texto + binário)", 
                       command=mesclar_traducao_completa, bg="#ff6b6b", fg="white", height=2)
btn_mesclar.pack(fill=tk.X)

# Status bar
status_var = tk.StringVar()
status_var.set("MODO: Extração completa | Detecção inteligente de células traduzidas")
status_bar = tk.Label(root, textvariable=status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, fg="green")
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

# Verifica se o arquivo binário existe
if not os.path.exists(BIN_FILE):
    status_var.set(f"AVISO: Arquivo {BIN_FILE} não encontrado! Configure o caminho correto.")

root.mainloop()
