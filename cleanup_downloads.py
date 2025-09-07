#!/usr/bin/env python3
"""
Script para limpar arquivos de download corrompidos ou incompletos
"""

import os
import glob

def cleanup_downloads():
    """Remove arquivos temporários e corrompidos da pasta de downloads"""
    downloads_dir = os.path.join('src', 'downloads')
    
    if not os.path.exists(downloads_dir):
        print("Pasta de downloads não encontrada.")
        return
    
    # Padrões de arquivos para remover
    patterns_to_remove = [
        '*.part',      # Arquivos parciais
        '*.temp.*',    # Arquivos temporários
        '*.f[0-9]*.*', # Arquivos de formato específico (geralmente sem áudio)
    ]
    
    removed_files = []
    
    for pattern in patterns_to_remove:
        files = glob.glob(os.path.join(downloads_dir, pattern))
        for file_path in files:
            try:
                os.remove(file_path)
                removed_files.append(os.path.basename(file_path))
                print(f"Removido: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Erro ao remover {file_path}: {e}")
    
    if removed_files:
        print(f"\nTotal de {len(removed_files)} arquivos removidos.")
        print("Agora tente baixar o vídeo novamente.")
    else:
        print("Nenhum arquivo temporário encontrado para remover.")

if __name__ == "__main__":
    cleanup_downloads()