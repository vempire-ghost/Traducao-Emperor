import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import struct
import os
from pathlib import Path

class ZeusTextReaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Zeus Text File Reader")
        self.root.geometry("1200x800")
        
        self.filename = None
        self.data = None
        self.groups = []
        self.current_group_texts = []
        
        # Configurar estilo
        self.setup_styles()
        
        # Criar interface
        self.create_widgets()
        
    def setup_styles(self):
        """Configura estilos para a interface"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar cores
        self.root.configure(bg='#2b2b2b')
        style.configure('TLabel', background='#2b2b2b', foreground='white')
        style.configure('TFrame', background='#2b2b2b')
        style.configure('TButton', background='#3c3c3c', foreground='white')
        style.configure('Treeview', background='#1e1e1e', fieldbackground='#1e1e1e', foreground='white')
        style.map('Treeview', background=[('selected', '#0078d7')])
        
    def create_widgets(self):
        """Cria todos os widgets da interface"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # ========== BARRA SUPERIOR ==========
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Botão para abrir arquivo
        self.open_btn = ttk.Button(top_frame, text="📂 Abrir Arquivo", 
                                  command=self.open_file, width=20)
        self.open_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Label com nome do arquivo
        self.file_label = ttk.Label(top_frame, text="Nenhum arquivo aberto")
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Botão para exportar
        self.export_btn = ttk.Button(top_frame, text="📤 Exportar Dados", 
                                    command=self.export_data, state=tk.DISABLED)
        self.export_btn.pack(side=tk.RIGHT)
        
        # ========== INFORMAÇÕES DO ARQUIVO ==========
        info_frame = ttk.LabelFrame(main_frame, text="Informações do Arquivo", padding="10")
        info_frame.grid(row=1, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Grid para informações
        for i in range(6):
            info_frame.columnconfigure(i, weight=1)
        
        # Labels de informações
        self.info_labels = {}
        info_fields = [
            ("Tamanho:", "size", 0, 0),
            ("Assinatura:", "signature", 0, 1),
            ("Grupos:", "groups", 0, 2),
            ("Células:", "cells", 1, 0),
            ("Início Dados:", "data_start", 1, 1),
            ("Entradas Lista:", "list_entries", 1, 2),
        ]
        
        for text, key, row, col in info_fields:
            frame = ttk.Frame(info_frame)
            frame.grid(row=row, column=col*2, padx=(0, 5), pady=5, sticky=tk.W)
            
            ttk.Label(frame, text=text, font=('TkDefaultFont', 9, 'bold')).pack(side=tk.LEFT)
            self.info_labels[key] = ttk.Label(frame, text="-")
            self.info_labels[key].pack(side=tk.LEFT)
        
        # ========== LISTA DE GRUPOS ==========
        list_frame = ttk.LabelFrame(main_frame, text="Lista de Grupos", padding="10")
        list_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview para grupos
        columns = ('ID', 'Células', 'Ponteiro', 'Offset', 'Endereço')
        self.groups_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Configurar colunas
        col_widths = [50, 80, 100, 100, 120]
        for col, width in zip(columns, col_widths):
            self.groups_tree.heading(col, text=col)
            self.groups_tree.column(col, width=width, anchor=tk.CENTER)
        
        # Scrollbar
        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.groups_tree.yview)
        self.groups_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Layout
        self.groups_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Bind de seleção
        self.groups_tree.bind('<<TreeviewSelect>>', self.on_group_select)
        
        # ========== TEXTO DO GRUPO SELECIONADO ==========
        text_frame = ttk.LabelFrame(main_frame, text="Texto do Grupo Selecionado", padding="10")
        text_frame.grid(row=2, column=2, pady=(0, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)
        
        # Controles do texto
        text_top_frame = ttk.Frame(text_frame)
        text_top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(text_top_frame, text="Grupo:").pack(side=tk.LEFT)
        self.group_id_label = ttk.Label(text_top_frame, text="-", font=('TkDefaultFont', 9, 'bold'))
        self.group_id_label.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(text_top_frame, text="Células:").pack(side=tk.LEFT)
        self.group_cells_label = ttk.Label(text_top_frame, text="-")
        self.group_cells_label.pack(side=tk.LEFT)
        
        # Área de texto com scroll
        self.text_area = scrolledtext.ScrolledText(
            text_frame, 
            wrap=tk.WORD, 
            width=40, 
            height=20,
            bg='#1e1e1e',
            fg='white',
            insertbackground='white'
        )
        self.text_area.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ========== ESTATÍSTICAS ==========
        stats_frame = ttk.LabelFrame(main_frame, text="Estatísticas", padding="10")
        stats_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E, tk.N, tk.S))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.rowconfigure(0, weight=1)
        
        # Área de texto para estatísticas
        self.stats_text = scrolledtext.ScrolledText(
            stats_frame,
            wrap=tk.WORD,
            height=8,
            bg='#1e1e1e',
            fg='white',
            state=tk.DISABLED
        )
        self.stats_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ========== BARRA DE STATUS ==========
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.status_label = ttk.Label(status_frame, text="Pronto")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)
        
    def open_file(self):
        """Abre um arquivo para análise"""
        filename = filedialog.askopenfilename(
            title="Selecionar arquivo Zeus_Text.eng",
            filetypes=[("Arquivos Zeus", "*.eng"), ("Todos os arquivos", "*.*")]
        )
        
        if filename:
            self.filename = filename
            self.file_label.config(text=f"Arquivo: {Path(filename).name}")
            self.analyze_file()
    
    def analyze_file(self):
        """Analisa o arquivo selecionado - VERSÃO COMPLETA COM HEX/ASCII"""
        try:
            self.status_label.config(text="Lendo arquivo...")
            self.root.update()
            
            # Ler arquivo
            with open(self.filename, 'rb') as f:
                self.data = f.read()
            
            # Limpar dados anteriores
            self.groups = []
            self.groups_tree.delete(*self.groups_tree.get_children())
            self.text_area.delete(1.0, tk.END)
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            
            # Analisar assinatura
            signature = self.data[0:16]
            self.info_labels['signature'].config(text=signature.hex(' ').upper()[:20] + "...")
            self.info_labels['size'].config(text=f"{len(self.data):,} bytes")
            
            # Analisar cabeçalho
            header_values = []
            for i in range(16, 32, 4):
                value = struct.unpack('<I', self.data[i:i+4])[0]
                header_values.append(value)
            
            # Analisar lista
            data_start = 0x1F5C
            list_start = 0x20
            list_data = self.data[list_start:data_start]
            list_entries = []
            
            for i in range(0, len(list_data), 4):
                value = struct.unpack('<I', list_data[i:i+4])[0]
                list_entries.append(value)
            
            # Configurar colunas COM HEX/ASCII
            columns = ('Pos', 'Hex Valor', 'ASCII', 'Células', 'Ponteiro', 'Offset', 'Endereço')
            self.groups_tree['columns'] = columns
            self.groups_tree['show'] = 'headings'
            
            # Configurar larguras das colunas
            col_widths = [50, 90, 100, 70, 90, 90, 100]
            for col, width in zip(columns, col_widths):
                self.groups_tree.heading(col, text=col)
                self.groups_tree.column(col, width=width, anchor=tk.CENTER)
            
            # Processar grupos - MANTER ORDEM ORIGINAL
            total_cells = 0
            
            self.progress_var.set(0)
            total_pairs = (len(list_entries) - 2) // 2
            
            table_position = 1  # Posição 1-based na tabela
            
            for i in range(2, len(list_entries), 2):
                if i + 1 >= len(list_entries):
                    break
                
                # CORREÇÃO: Pegar os bytes ORIGINAIS do arquivo
                # O valor Tipo 2 está em list_data, não em list_entries (que já foi convertido)
                byte_position = list_start + (i * 4)  # Posição dos bytes no arquivo
                
                # Pegar os 4 bytes ORIGINAIS do valor
                original_bytes = self.data[byte_position:byte_position + 4]
                hex_value = original_bytes.hex(' ').upper()
                
                # Tentar interpretar como ASCII (pode não ser texto)
                ascii_repr = ""
                for byte in original_bytes:
                    if 32 <= byte <= 126:  # Caracteres ASCII imprimíveis
                        ascii_repr += chr(byte)
                    elif byte == 0:
                        ascii_repr += "\\0"
                    else:
                        ascii_repr += "."
                
                # Valores decodificados
                cell_count = list_entries[i]
                pointer = list_entries[i + 1]
                data_offset = data_start + pointer
                
                self.groups.append({
                    'table_position': table_position,
                    'original_bytes': original_bytes,
                    'hex_value': hex_value,
                    'ascii_repr': ascii_repr,
                    'cells': cell_count,
                    'pointer': pointer,
                    'offset': data_offset,
                    'hex_offset': f"0x{data_offset:08X}",
                    'original_index': i
                })
                
                # Adicionar à treeview
                self.groups_tree.insert('', tk.END, values=(
                    table_position,
                    hex_value,
                    ascii_repr,
                    cell_count,
                    f"0x{pointer:08X}",
                    data_offset,
                    f"0x{data_offset:08X}"
                ))
                
                total_cells += cell_count
                table_position += 1
                
                # Atualizar progresso
                if table_position % 10 == 0 or table_position == total_pairs:
                    progress = (table_position / total_pairs) * 100
                    self.progress_var.set(progress)
                    self.status_label.config(text=f"Processando... {table_position}/{total_pairs} grupos")
                    self.root.update()
            
            self.progress_var.set(100)
            
            # Adicionar também os valores formais (0, 0) no início para referência
            self.add_formal_entries(list_start)
            
            # Atualizar informações
            self.info_labels['groups'].config(text=str(len(self.groups)))
            self.info_labels['cells'].config(text=str(total_cells))
            self.info_labels['list_entries'].config(text=str(len(list_entries)))
            self.info_labels['data_start'].config(text=f"0x{data_start:08X}")
            
            # Verificar consistência
            header_cells = header_values[1] if len(header_values) > 1 else 0
            status_text = f"Análise concluída - {len(self.groups)} grupos, {total_cells} células"
            if header_cells != 0 and header_cells != total_cells:
                status_text += f" (Cabeçalho: {header_cells})"
            
            self.status_label.config(text=status_text)
            
            # Calcular estatísticas
            self.calculate_statistics()
            
            # Habilitar exportação
            self.export_btn.config(state=tk.NORMAL)
            
            # Atualizar método de seleção
            self.groups_tree.bind('<<TreeviewSelect>>', self.on_group_select_with_details)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao analisar arquivo:\n{str(e)}")
            self.status_label.config(text="Erro na análise")

    def add_formal_entries(self, list_start):
        """Adiciona os valores formais (0, 0) no início da tabela para referência"""
        # Pegar os bytes dos valores formais
        formal1_bytes = self.data[list_start:list_start + 4]  # Primeiro 0
        formal2_bytes = self.data[list_start + 4:list_start + 8]  # Segundo 0
        
        formal1_hex = formal1_bytes.hex(' ').upper()
        formal2_hex = formal2_bytes.hex(' ').upper()
        
        # Converter para ASCII para display
        def bytes_to_ascii(byte_data):
            ascii_str = ""
            for byte in byte_data:
                if 32 <= byte <= 126:
                    ascii_str += chr(byte)
                elif byte == 0:
                    ascii_str += "\\0"
                else:
                    ascii_str += "."
            return ascii_str
        
        # Inserir na PRIMEIRA POSIÇÃO da treeview
        self.groups_tree.insert('', 0, values=(
            "FORMAL",
            formal1_hex,
            bytes_to_ascii(formal1_bytes),
            "0",
            "0x00000000",
            "N/A",
            "N/A"
        ), tags=('formal',))
        
        self.groups_tree.insert('', 1, values=(
            "FORMAL",
            formal2_hex,
            bytes_to_ascii(formal2_bytes),
            "0",
            "0x00000000",
            "N/A",
            "N/A"
        ), tags=('formal',))
        
        # Configurar cor diferente para formais
        self.groups_tree.tag_configure('formal', background='#333333', foreground='#AAAAAA')

    def on_group_select_with_details(self, event):
        """Handler de seleção que mostra detalhes HEX/ASCII"""
        selection = self.groups_tree.selection()
        if not selection:
            return
        
        item = self.groups_tree.item(selection[0])
        values = item['values']
        
        # Ignorar cliques nos formais
        if values[0] == "FORMAL":
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(1.0, "Valores formais (sempre 0, 0)")
            self.group_id_label.config(text="FORMAL")
            self.group_cells_label.config(text="0 células")
            return
        
        table_position = int(values[0])
        
        # Encontrar grupo
        group = next((g for g in self.groups if g['table_position'] == table_position), None)
        if not group:
            return
        
        # Atualizar labels
        self.group_id_label.config(text=f"Posição {table_position}")
        self.group_cells_label.config(text=f"{group['cells']} células")
        
        # Mostrar detalhes HEX/ASCII
        self.show_group_details(group)

    def show_group_details(self, group):
        """Mostra detalhes HEX/ASCII do grupo"""
        self.text_area.delete(1.0, tk.END)
        
        # Criar cabeçalho detalhado
        details = f"DETALHES DO GRUPO NA POSIÇÃO {group['table_position']}\n"
        details += "=" * 60 + "\n\n"
        
        # Bytes brutos do valor Tipo 2
        details += "BYTES DO VALOR TIPO 2 (Células):\n"
        details += f"  Hex:    {group['hex_value']}\n"
        details += f"  ASCII:  {group['ascii_repr']}\n"
        details += f"  Decimal: {group['cells']}\n\n"
        
        # Informações decodificadas
        details += "INFORMAÇÕES DECODIFICADAS:\n"
        details += f"  Número de células: {group['cells']}\n"
        details += f"  Ponteiro: 0x{group['pointer']:08X} ({group['pointer']} decimal)\n"
        details += f"  Offset no arquivo: {group['offset']} (0x{group['offset']:08X})\n"
        details += f"  Posição relativa: +{group['pointer']} bytes do início dos dados\n\n"
        
        # Mostrar bytes em diferentes formatos
        details += "ANÁLISE DOS 4 BYTES:\n"
        bytes_list = list(group['original_bytes'])
        
        # Little-endian (como está no arquivo)
        details += "  Little-endian (arquivo):\n"
        for j, byte in enumerate(bytes_list):
            details += f"    Byte {j}: 0x{byte:02X} = {byte:3d} = "
            if 32 <= byte <= 126:
                details += f"'{chr(byte)}'\n"
            elif byte == 0:
                details += "NULL\n"
            else:
                details += ".\n"
        
        # Big-endian (para comparação)
        details += "\n  Big-endian (invertido):\n"
        for j, byte in enumerate(reversed(bytes_list)):
            details += f"    Byte {j}: 0x{byte:02X} = {byte:3d} = "
            if 32 <= byte <= 126:
                details += f"'{chr(byte)}'\n"
            elif byte == 0:
                details += "NULL\n"
            else:
                details += ".\n"
        
        # Interpretações possíveis
        details += "\nINTERPRETAÇÕES POSSÍVEIS:\n"
        
        # 1. Apenas número de células
        details += f"  1. Apenas número de células: {group['cells']}\n"
        
        # 2. Se fosse (ID << 16) | células
        high_word = (group['cells'] >> 16) & 0xFFFF
        low_word = group['cells'] & 0xFFFF
        details += f"  2. Como (ID<<16)|Células: ID={high_word}, Células={low_word}\n"
        
        # 3. Se cada byte fosse algo diferente
        details += "  3. Bytes individuais como valores:\n"
        for j, byte in enumerate(bytes_list):
            details += f"     Byte {j}: {byte} "
            if byte == 0:
                details += "(provavelmente padding)\n"
            elif byte < 10:
                details += f"(pequeno valor)\n"
            else:
                details += "\n"
        
        details += "\n" + "=" * 60 + "\n\n"
        
        # Agora extrair os textos reais
        details += "TEXTOS DO GRUPO:\n"
        details += "=" * 60 + "\n\n"
        
        texts = self.extract_group_texts_for_display(group['offset'], group['cells'])
        if texts:
            details += "\n\n".join(texts)
        else:
            details += "Nenhum texto encontrado ou grupo vazio"
        
        self.text_area.insert(1.0, details)

    def extract_group_texts_for_display(self, offset, cell_count):
        """Extrai textos para display"""
        texts = []
        current_pos = offset
        
        for cell_num in range(cell_count):
            end_pos = self.data.find(b'\x00', current_pos)
            if end_pos == -1:
                texts.append(f"[Célula {cell_num + 1}] <FIM INESPERADO DO ARQUIVO>")
                break
            
            text_data = self.data[current_pos:end_pos]
            
            # Mostrar tanto HEX quanto ASCII
            hex_repr = text_data.hex(' ').upper()[:50]
            if len(text_data) > 16:
                hex_repr += "..."
            
            try:
                ascii_text = text_data.decode('ascii', errors='replace')
                ascii_text = ascii_text.replace('@L', '\\n').replace('@', '@')
                if len(ascii_text) > 50:
                    ascii_text = ascii_text[:47] + "..."
            except:
                ascii_text = f"<{len(text_data)} bytes binários>"
            
            texts.append(f"[Célula {cell_num + 1}]\n  Hex: {hex_repr}\n  Texto: {ascii_text}")
            current_pos = end_pos + 1
        
        return texts
    
    def calculate_statistics(self):
        """Calcula e exibe estatísticas"""
        if not self.groups:
            return
        
        cell_counts = [g['cells'] for g in self.groups]
        
        stats = [
            f"TOTAL DE GRUPOS: {len(self.groups)}",
            f"TOTAL DE CÉLULAS: {sum(cell_counts)}",
            f"MAIOR GRUPO: {max(cell_counts)} células",
            f"MENOR GRUPO: {min(cell_counts)} células",
            f"MÉDIA: {sum(cell_counts)/len(cell_counts):.2f} células/grupo",
            "\nDISTRIBUIÇÃO:"
        ]
        
        # Distribuição
        distrib = {}
        for count in cell_counts:
            distrib[count] = distrib.get(count, 0) + 1
        
        # Ordenar por frequência
        sorted_distrib = sorted(distrib.items(), key=lambda x: x[1], reverse=True)
        
        for count, freq in sorted_distrib[:15]:  # Mostrar top 15
            stats.append(f"  {count:3d} células: {freq:3d} grupos ({freq/len(self.groups)*100:.1f}%)")
        
        if len(sorted_distrib) > 15:
            stats.append(f"  ... e mais {len(sorted_distrib) - 15} tamanhos diferentes")
        
        # Exibir estatísticas
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, "\n".join(stats))
        self.stats_text.config(state=tk.DISABLED)
    
    def on_group_select(self, event):
        """Quando um grupo é selecionado na treeview"""
        selection = self.groups_tree.selection()
        if not selection:
            return
        
        item = self.groups_tree.item(selection[0])
        group_id = int(item['values'][0])
        
        # Encontrar grupo
        group = next((g for g in self.groups if g['id'] == group_id), None)
        if not group:
            return
        
        # Atualizar labels
        self.group_id_label.config(text=str(group_id))
        self.group_cells_label.config(text=str(group['cells']))
        
        # Extrair textos do grupo
        self.extract_group_texts(group_id)
    
    def extract_group_texts(self, group_id):
        """Extrai e exibe os textos de um grupo"""
        group = self.groups[group_id - 1]
        
        # Limpar área de texto
        self.text_area.delete(1.0, tk.END)
        
        # Extrair textos
        texts = []
        current_pos = group['offset']
        
        for cell_num in range(group['cells']):
            # Encontrar próximo byte nulo
            end_pos = self.data.find(b'\x00', current_pos)
            if end_pos == -1:
                break
            
            text_data = self.data[current_pos:end_pos]
            
            # Tentar decodificar
            try:
                text = text_data.decode('ascii', errors='replace')
                # Substituir caracteres especiais
                text = text.replace('@L', '\\n').replace('@', '@')
                texts.append(f"[Célula {cell_num + 1}] {text}")
            except:
                texts.append(f"[Célula {cell_num + 1}] <Dados binários: {len(text_data)} bytes>")
            
            current_pos = end_pos + 1
        
        # Exibir textos
        if texts:
            self.text_area.insert(1.0, "\n\n".join(texts))
        else:
            self.text_area.insert(1.0, "Nenhum texto encontrado ou grupo vazio")
        
        self.current_group_texts = texts
    
    def export_data(self):
        """Exporta os dados analisados"""
        if not self.groups:
            messagebox.showwarning("Exportar", "Nenhum dado para exportar")
            return
        
        # Perguntar onde salvar
        filename = filedialog.asksaveasfilename(
            title="Salvar análise",
            defaultextension=".txt",
            filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"ANÁLISE DO ARQUIVO: {Path(self.filename).name}\n")
                f.write("=" * 60 + "\n\n")
                
                # Informações gerais
                f.write("INFORMAÇÕES GERAIS:\n")
                f.write(f"Tamanho do arquivo: {len(self.data):,} bytes\n")
                f.write(f"Número de grupos: {len(self.groups)}\n")
                f.write(f"Número total de células: {sum(g['cells'] for g in self.groups)}\n\n")
                
                # Lista de grupos
                f.write("LISTA DE GRUPOS:\n")
                f.write(f"{'ID':<6} {'Células':<8} {'Ponteiro':<12} {'Offset':<12} {'Endereço'}\n")
                f.write("-" * 60 + "\n")
                
                for group in self.groups:
                    f.write(f"{group['id']:<6} {group['cells']:<8} 0x{group['pointer']:08X}  "
                           f"{group['offset']:<12} {group['hex_offset']}\n")
                
                # Textos do grupo selecionado (se houver)
                if self.current_group_texts:
                    f.write(f"\n\nTEXTOS DO GRUPO {self.group_id_label['text']}:\n")
                    f.write("=" * 60 + "\n")
                    for text in self.current_group_texts:
                        f.write(text + "\n")
                
            messagebox.showinfo("Exportar", f"Dados exportados com sucesso para:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar dados:\n{str(e)}")
    
    def run(self):
        """Executa a aplicação"""
        self.root.mainloop()

def main():
    root = tk.Tk()
    app = ZeusTextReaderGUI(root)
    app.run()

if __name__ == "__main__":
    main()
