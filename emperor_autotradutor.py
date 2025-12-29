#!/usr/bin/env python3
"""
ZEUS DEEPL TRANSLATOR - VERSÃO QUE FUNCIONA
Edita o arquivo Zeus_Text_TRADUZIR.txt com DeepL REAL
IGNORA STRINGS COM MENOS DE 3 CARACTERES
"""

import re
import os
import sys
import time
import requests
import argparse
from typing import List, Dict

# ==================== DEEPL API REAL ====================

class DeepLTranslator:
    """Tradutor usando DeepL API - VERSÃO CORRETA"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "0a4125d7-a3db-43ca-8ac2-cb581aee42a4:fx"
        
        # Decidir qual endpoint usar baseado na chave
        if self.api_key.endswith(":fx"):
            self.base_url = "https://api-free.deepl.com/v2/translate"
        else:
            self.base_url = "https://api.deepl.com/v2/translate"
        
        self.session = requests.Session()
        
    def translate(self, text: str, source_lang: str = "EN", target_lang: str = "PT-BR") -> str:
        """Traduz usando DeepL API - IGNORA strings com menos de 3 caracteres"""
        # Ignorar strings com menos de 3 caracteres
        if not text or len(text.strip()) < 4:
            print(f"   ⏭️  Pulando string muito curta: '{text}'")
            return text
        
        try:
            # Limitar tamanho para evitar problemas
            clean_text = text.strip()
            if len(clean_text) > 1000:
                clean_text = clean_text[:1000]
            
            # Parâmetros CORRETOS para DeepL
            params = {
                "auth_key": self.api_key,
                "text": clean_text,
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = self.session.post(
                self.base_url,
                data=params,
                headers=headers,
                timeout=30
            )
            
            print(f"   🔍 API Response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if "translations" in result and result["translations"]:
                    translated = result["translations"][0]["text"]
                    print(f"   ✅ Traduzido: '{text[:30]}...' → '{translated[:30]}...'")
                    return translated
                else:
                    print(f"   ⚠️  Resposta inválida: {result}")
            elif response.status_code == 429:
                print("   ⏳ Rate limit, esperando 2s...")
                time.sleep(2)
                return self.translate(text, source_lang, target_lang)
            else:
                print(f"   ❌ Erro DeepL {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Erro na tradução: {str(e)}")
        
        return text  # Fallback

# ==================== PARSER CORRETO ====================

def parse_translation_file(filename: str):
    """Parseia o arquivo CORRETAMENTE - VERSÃO FUNCIONAL"""
    print(f"📖 Analisando arquivo: {filename}")
    
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    strings = []
    current_string = {}
    
    for i, line in enumerate(lines):
        line = line.rstrip('\n')
        
        # OFFSET: 0x...
        if line.startswith('OFFSET: 0x'):
            if current_string:
                strings.append(current_string)
            
            # Novo bloco
            match = re.search(r'OFFSET:\s*0x([0-9A-F]+)', line, re.IGNORECASE)
            if match:
                current_string = {
                    'offset': match.group(1),
                    'offset_line': i,
                    'original_line': i + 1,
                    'translation_line': -1,
                    'original': '',
                    'length': 0,
                    'existing_translation': '',
                    'has_translation': False
                }
        
        # ORIGINAL [X chars]: texto
        elif 'ORIGINAL [' in line and 'chars]:' in line and current_string:
            match = re.search(r'\[(\d+)\s*chars\]:\s*(.+)', line)
            if match:
                current_string['length'] = int(match.group(1))
                current_string['original'] = match.group(2).strip()
        
        # TRADUÇÃO:
        elif line.strip() == 'TRADUÇÃO:' and current_string:
            if i + 1 < len(lines) and not lines[i + 1].startswith('OFFSET:'):
                current_string['translation_line'] = i + 1
                existing = lines[i + 1].rstrip('\n')
                current_string['existing_translation'] = existing
                current_string['has_translation'] = bool(existing.strip())
    
    # Adicionar última string
    if current_string:
        strings.append(current_string)
    
    print(f"✅ Encontradas {len(strings)} strings")
    
    # Contar traduções existentes
    translated = sum(1 for s in strings if s['has_translation'])
    print(f"📝 Já traduzidas: {translated}")
    print(f"📝 Para traduzir: {len(strings) - translated}")
    
    return strings, lines

# ==================== EDITOR DE ARQUIVO ====================

def edit_translation_file(filename: str, overwrite: bool = False, limit: int = 0):
    """Edita o arquivo CORRETAMENTE - IGNORA strings com menos de 3 caracteres"""
    
    print(f"\n🎯 EDITANDO: {filename}")
    print(f"⚙️  Modo: {'SOBRESCREVER TUDO' if overwrite else 'APENAS VAZIAS'}")
    print(f"📏 Config: Ignorando strings com menos de 3 caracteres")
    
    # Criar backup
    backup_file = f"{filename}.backup"
    import shutil
    shutil.copy2(filename, backup_file)
    print(f"💾 Backup criado: {backup_file}")
    
    # Parsear arquivo
    strings, lines = parse_translation_file(filename)
    
    # Inicializar tradutor
    translator = DeepLTranslator()
    
    # Estatísticas
    stats = {
        'total': len(strings),
        'translated_now': 0,
        'skipped': 0,
        'errors': 0,
        'short_skipped': 0  # Para contar strings curtas puladas
    }
    
    start_time = time.time()
    
    # Limitar se necessário
    if limit > 0 and limit < len(strings):
        strings = strings[:limit]
        print(f"⚠️  Limitado às primeiras {limit} strings")
    
    # Processar cada string
    for idx, s in enumerate(strings):
        # Progresso
        if idx % 50 == 0 and idx > 0:
            elapsed = time.time() - start_time
            percent = (idx / len(strings)) * 100
            print(f"📊 {idx}/{len(strings)} ({percent:.1f}%) - {elapsed:.0f}s")
        
        # Verificar se já tem tradução
        if s['has_translation'] and not overwrite:
            stats['skipped'] += 1
            continue
        
        # Verificar linha de tradução
        trans_line = s['translation_line']
        if trans_line < 0 or trans_line >= len(lines):
            stats['skipped'] += 1
            continue
        
        # Pular strings vazias ou muito curtas (MENOS DE 3 CARACTERES)
        if not s['original'] or len(s['original'].strip()) < 4:
            print(f"\n[{idx+1}] ⏭️  Pulando string muito curta: '{s['original']}'")
            stats['skipped'] += 1
            stats['short_skipped'] += 1
            continue
        
        # TRADUZIR COM DEEPL
        try:
            print(f"\n[{idx+1}] Traduzindo: '{s['original'][:40]}...'")
            
            # Chamar DeepL
            translated_text = translator.translate(s['original'])
            
            if translated_text and translated_text != s['original']:
                # Ajustar para tamanho exato
                if len(translated_text) > s['length']:
                    translated_text = translated_text[:s['length']]
                elif len(translated_text) < s['length']:
                    translated_text = translated_text.ljust(s['length'])
                
                # ATUALIZAR LINHA NO ARQUIVO
                lines[trans_line] = translated_text + '\n'
                stats['translated_now'] += 1
                
                print(f"   ✅ Salvo na linha {trans_line + 1}: '{translated_text[:40]}...'")
                
                # Salvar a cada 10 traduções
                if stats['translated_now'] % 10 == 0:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    print(f"   💾 Auto-save ({stats['translated_now']} traduções)")
            else:
                print(f"   ⚠️  Tradução falhou ou igual ao original")
                stats['skipped'] += 1
            
            # Pausa para não sobrecarregar API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")
            stats['errors'] += 1
            continue
    
    # Salvar arquivo FINAL
    print(f"\n💾 Salvando arquivo final...")
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    elapsed = time.time() - start_time
    
    # Relatório
    print(f"\n{'='*60}")
    print("📊 RELATÓRIO FINAL")
    print(f"{'='*60}")
    print(f"   • Arquivo: {filename}")
    print(f"   • Strings totais: {stats['total']}")
    print(f"   • Traduzidas AGORA: {stats['translated_now']}")
    print(f"   • Puladas (curtas <3 chars): {stats['short_skipped']}")
    print(f"   • Puladas (outros motivos): {stats['skipped'] - stats['short_skipped']}")
    print(f"   • Erros: {stats['errors']}")
    print(f"   • Tempo total: {elapsed:.1f}s")
    
    if stats['translated_now'] > 0:
        speed = stats['translated_now'] / elapsed if elapsed > 0 else 0
        print(f"   • Velocidade: {speed:.1f} strings/s")
        
        # Verificar se as traduções foram salvas
        print(f"\n🔍 VERIFICAÇÃO:")
        
        # Ler primeiras 5 strings traduzidas
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar exemplos de traduções
        import re
        translations = re.findall(r'TRADUÇÃO:\s*\n(.+)', content)
        
        if translations:
            print(f"   ✅ Encontradas {len(translations)} linhas 'TRADUÇÃO:' no arquivo")
            print(f"   📝 Primeiras 3 traduções salvas:")
            for i, trans in enumerate(translations[:3]):
                if trans.strip() and not trans.strip().startswith('OFFSET:'):
                    print(f"      {i+1}. '{trans[:50]}...'")
        else:
            print(f"   ❌ NENHUMA tradução encontrada no arquivo!")
        
        print(f"\n💡 Dica: Abra o arquivo e procure por 'TRADUÇÃO:' para ver as mudanças")
    
    print(f"{'='*60}")
    return stats['translated_now'] > 0

def main():
    parser = argparse.ArgumentParser(
        description="ZEUS DEEPL TRANSLATOR - Ignora strings com menos de 3 caracteres",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("arquivo", help="Zeus_Text_TRADUZIR.txt")
    parser.add_argument("--overwrite", action="store_true",
                       help="Sobrescrever traduções existentes")
    parser.add_argument("--limit", type=int, default=0,
                       help="Limitar número de strings (0 = todas)")
    parser.add_argument("--api-key", 
                       default="0a4125d7-a3db-43ca-8ac2-cb581aee42a4:fx",
                       help="DeepL API Key (padrão: chave gratuita)")
    
    args = parser.parse_args()
    
    print(f"{'='*60}")
    print("ZEUS DEEPL TRANSLATOR - IGNORA STRINGS CURTAS (<3 chars)")
    print(f"{'='*60}")
    
    if not os.path.exists(args.arquivo):
        print(f"❌ Arquivo não existe: {args.arquivo}")
        sys.exit(1)
    
    # Executar tradução
    success = edit_translation_file(
        filename=args.arquivo,
        overwrite=args.overwrite,
        limit=args.limit
    )
    
    if success:
        print(f"\n✅ TRADUÇÃO CONCLUÍDA!")
        print(f"   Abra o arquivo '{args.arquivo}' para ver as mudanças.")
    else:
        print(f"\n⚠️  Nenhuma tradução foi aplicada.")
        print(f"   Verifique se as strings já estão traduzidas ou use --overwrite")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
