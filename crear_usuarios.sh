#!/bin/bash

ARCHIVO_USUARIOS=""
PASSWORD=""
VERBOSE=false
FORCE_PASSWORD=false

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

while getopts "f:p:vh" opcion; do
    case $opcion in
        f)
            ARCHIVO_USUARIOS="$OPTARG"
            ;;
        p)
            PASSWORD="$OPTARG"
            FORCE_PASSWORD=true
            ;;
        v)
            VERBOSE=true
            ;;
        h)
            echo "Uso: $0 -f ARCHIVO [-p PASSWORD] [-v]"
            echo ""
            echo "Opciones:"
            echo "  -f ARCHIVO    Archivo con la información de usuarios (obligatorio)"
            echo "  -p PASSWORD   Contraseña para todos los usuarios (opcional)"
            echo "  -v            Modo verbose - muestra información detallada"
            echo "  -h            Muestra esta ayuda"
            echo ""
            echo "Formato del archivo de usuarios (un usuario por línea):"
            echo "  usuario:shell:home:comentario:crear_home"
            echo ""
            echo "Ejemplo:"
            echo "  juan:/bin/bash:/home/juan:Juan Pérez:yes"
            echo "  maria:/bin/sh:/home/maria:María García:no"
            exit 0
            ;;
        \?)
            echo -e "${RED}Opción inválida: -$OPTARG${NC}" >&2
            echo "Uso: $0 -f ARCHIVO [-p PASSWORD] [-v]"
            exit 1
            ;;
    esac
done

if [ -z "$ARCHIVO_USUARIOS" ]; then
    echo -e "${RED}Error: Debe especificar un archivo con la opción -f${NC}"
    exit 1
fi

if [ ! -f "$ARCHIVO_USUARIOS" ]; then
    echo -e "${RED}Error: El archivo '$ARCHIVO_USUARIOS' no existe${NC}"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Este script debe ejecutarse como root (usar sudo)${NC}"
    exit 1
fi

usuarios_creados=0
usuarios_fallidos=0
usuarios_existentes=0

echo "Procesando archivo: $ARCHIVO_USUARIOS"
echo "=========================================="

linea_num=0
while IFS= read -r linea || [ -n "$linea" ]; do
    linea_num=$((linea_num + 1))
    
    if [[ -z "$linea" ]] || [[ "$linea" =~ ^[[:space:]]*# ]]; then
        continue
    fi
    
    linea=$(echo "$linea" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    IFS=':' read -r usuario shell home_dir comentario crear_home <<< "$linea"
    
    if [ -z "$usuario" ]; then
        echo -e "${YELLOW}[ADVERTENCIA]${NC} Línea $linea_num: Usuario vacío, se omite"
        continue
    fi
    
    password_usuario="$PASSWORD"
    
    if id "$usuario" &>/dev/null; then
        echo -e "${YELLOW}[INFO]${NC} Usuario '$usuario' ya existe. Se omite."
        usuarios_existentes=$((usuarios_existentes + 1))
        continue
    fi
    
    comando="useradd"
    
    if [ -n "$shell" ] && [ "$shell" != "-" ]; then
        if [ ! -f "$shell" ]; then
            echo -e "${RED}[ERROR]${NC} Shell '$shell' no existe para usuario '$usuario'"
            usuarios_fallidos=$((usuarios_fallidos + 1))
            continue
        fi
        comando="$comando -s $shell"
    fi
    
    if [ -n "$home_dir" ] && [ "$home_dir" != "-" ]; then
        comando="$comando -d $home_dir"
    fi
    
    if [ -n "$comentario" ] && [ "$comentario" != "-" ]; then
        comando="$comando -c \"$comentario\""
    fi
    
    if [ "$crear_home" = "yes" ] || [ "$crear_home" = "YES" ] || [ "$crear_home" = "1" ]; then
        comando="$comando -m"
    else
        comando="$comando -M"
    fi
    
    comando="$comando $usuario"
    
    if [ "$VERBOSE" = true ]; then
        echo -e "${YELLOW}[DEBUG]${NC} Ejecutando: $comando"
    fi
    
    if eval "$comando" 2>/dev/null; then
        if [ -n "$password_usuario" ] && [ "$password_usuario" != "-" ]; then
            echo "$usuario:$password_usuario" | chpasswd 2>/dev/null
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}[ÉXITO]${NC} Usuario '$usuario' creado correctamente con contraseña"
            else
                echo -e "${YELLOW}[ADVERTENCIA]${NC} Usuario '$usuario' creado pero no se pudo establecer la contraseña"
            fi
        else
            echo -e "${GREEN}[ÉXITO]${NC} Usuario '$usuario' creado correctamente"
        fi
        usuarios_creados=$((usuarios_creados + 1))
    else
        echo -e "${RED}[ERROR]${NC} No se pudo crear el usuario '$usuario'"
        usuarios_fallidos=$((usuarios_fallidos + 1))
    fi
    
done < "$ARCHIVO_USUARIOS"

echo ""
echo "=========================================="
echo "Resumen:"
echo -e "  ${GREEN}Usuarios creados: $usuarios_creados${NC}"
if [ $usuarios_existentes -gt 0 ]; then
    echo -e "  ${YELLOW}Usuarios ya existentes: $usuarios_existentes${NC}"
fi
if [ $usuarios_fallidos -gt 0 ]; then
    echo -e "  ${RED}Usuarios con errores: $usuarios_fallidos${NC}"
fi

exit 0
