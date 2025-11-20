#!/bin/bash

# Script para crear usuarios desde un archivo
# Sintaxis: ej1_crea_usuarios.sh [-i] [-c contraseña] Archivo_con_los_usuarios_a_crear

# Códigos de error
ERROR_ARCHIVO_NO_EXISTE=1
ERROR_ARCHIVO_NO_REGULAR=2
ERROR_SIN_PERMISOS_LECTURA=3
ERROR_SINTAXIS_ARCHIVO=4
ERROR_PARAMETRO_INCORRECTO=5
ERROR_NUMERO_PARAMETROS=6
ERROR_OTRO=7

# Variables
ARCHIVO_USUARIOS=""
PASSWORD=""
MOSTRAR_INFO=false
usuarios_creados=0

# Verificar que se ejecuta como root
if [[ "$EUID" -ne 0 ]]; then
    echo "Error: Este script debe ejecutarse como root (usar sudo)" >&2
    exit $ERROR_OTRO
fi

# Procesar parámetros
tiene_archivo=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -i)
            MOSTRAR_INFO=true
            shift
            ;;
        -c)
            if [[ -z "$2" ]]; then
                echo "Error: La opción -c requiere un argumento (contraseña)" >&2
                exit $ERROR_PARAMETRO_INCORRECTO
            fi
            PASSWORD="$2"
            shift 2
            ;;
        -*)
            echo "Error: Modificador inválido: $1" >&2
            exit $ERROR_PARAMETRO_INCORRECTO
            ;;
        *)
            if [[ "$tiene_archivo" == true ]]; then
                echo "Error: Se especificó más de un archivo" >&2
                exit $ERROR_NUMERO_PARAMETROS
            fi
            ARCHIVO_USUARIOS="$1"
            tiene_archivo=true
            shift
            ;;
    esac
done

if [[ "$tiene_archivo" == false ]]; then
    echo "Error: Debe especificar un archivo con los usuarios a crear" >&2
    echo "Uso: $0 [-i] [-c contraseña] Archivo_con_los_usuarios_a_crear" >&2
    echo "" >&2
    echo "Opciones:" >&2
    echo "  -i              Muestra información sobre la creación de cada usuario" >&2
    echo "  -c contraseña    Asigna la contraseña especificada a todos los usuarios creados" >&2
    echo "  Archivo         Archivo con la información de usuarios (obligatorio)" >&2
    echo "" >&2
    echo "Formato del archivo (campos separados por :):" >&2
    echo "  usuario:comentario:directorio_home:crear_home(SI/NO):shell" >&2
    exit $ERROR_NUMERO_PARAMETROS
fi

# Validar archivo
if [[ ! -e "$ARCHIVO_USUARIOS" ]]; then
    echo "Error: El archivo '$ARCHIVO_USUARIOS' no existe" >&2
    exit $ERROR_ARCHIVO_NO_EXISTE
fi

if [[ ! -f "$ARCHIVO_USUARIOS" ]]; then
    echo "Error: '$ARCHIVO_USUARIOS' no es un archivo regular" >&2
    exit $ERROR_ARCHIVO_NO_REGULAR
fi

if [[ ! -r "$ARCHIVO_USUARIOS" ]]; then
    echo "Error: No se tienen permisos de lectura para '$ARCHIVO_USUARIOS'" >&2
    exit $ERROR_SIN_PERMISOS_LECTURA
fi

# Procesar archivo línea por línea
num_linea=0
errores_sintaxis=false
errores_creacion=false

while IFS= read -r linea || [[ -n "$linea" ]]; do
    num_linea=$((num_linea + 1))
    
    # Ignorar líneas vacías y comentarios
    linea_trimmed=$(echo "$linea" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [[ -z "$linea_trimmed" ]] || [[ "$linea_trimmed" =~ ^# ]]; then
        continue
    fi
    
    # Validar formato de línea (debe tener exactamente 5 campos separados por :)
    num_campos=$(echo "$linea_trimmed" | tr -cd ':' | wc -c)
    
    if [[ $num_campos -ne 4 ]]; then
        echo "Error: Línea $num_linea no contiene exactamente 5 campos separados por ':'" >&2
        echo "  Línea: $linea_trimmed" >&2
        errores_sintaxis=true
        continue
    fi
    
    # Extraer campos (usuario:comentario:home:crear_home:shell)
    IFS=':' read -r usuario comentario home_dir crear_home shell <<< "$linea_trimmed"
    
    # Validar que el usuario no esté vacío
    if [[ -z "$usuario" ]]; then
        echo "Error: Línea $num_linea - El nombre de usuario no puede estar vacío" >&2
        errores_sintaxis=true
        continue
    fi
    
    # Verificar si el usuario ya existe
    if id "$usuario" &>/dev/null; then
        if [[ "$MOSTRAR_INFO" == true ]]; then
            echo "Usuario '$usuario' (línea $num_linea): Ya existe, se omite"
        fi
        continue
    fi
    
    # Construir comando useradd usando array
    args=()
    
    # Agregar comentario si está definido
    if [[ -n "$comentario" ]]; then
        args+=(-c "$comentario")
    fi
    
    # Agregar directorio home si está definido
    if [[ -n "$home_dir" ]]; then
        args+=(-d "$home_dir")
    fi
    
    # Agregar opción de crear home
    if [[ "$crear_home" == "SI" ]] || [[ "$crear_home" == "si" ]] || [[ "$crear_home" == "Si" ]]; then
        args+=(-m)
    elif [[ "$crear_home" == "NO" ]] || [[ "$crear_home" == "no" ]] || [[ "$crear_home" == "No" ]]; then
        args+=(-M)
    fi
    
    # Agregar shell si está definido
    if [[ -n "$shell" ]]; then
        # Verificar que el shell existe
        if [[ ! -f "$shell" ]]; then
            if [[ "$MOSTRAR_INFO" == true ]]; then
                echo "Usuario '$usuario' (línea $num_linea): ERROR - Shell '$shell' no existe"
            fi
            errores_creacion=true
            continue
        fi
        args+=(-s "$shell")
    fi
    
    # Agregar nombre de usuario
    args+=("$usuario")
    
    # Ejecutar comando de creación
    if useradd "${args[@]}" 2>/dev/null; then
        # Asignar contraseña si se especificó
        if [[ -n "$PASSWORD" ]]; then
            if ! echo "$usuario:$PASSWORD" | chpasswd 2>/dev/null; then
                if [[ "$MOSTRAR_INFO" == true ]]; then
                    echo "Usuario '$usuario' (línea $num_linea): Creado pero no se pudo asignar contraseña"
                fi
                errores_creacion=true
                continue
            fi
        fi
        
        if [[ "$MOSTRAR_INFO" == true ]]; then
            echo "Usuario '$usuario' (línea $num_linea): Creado exitosamente"
        fi
        usuarios_creados=$((usuarios_creados + 1))
    else
        if [[ "$MOSTRAR_INFO" == true ]]; then
            echo "Usuario '$usuario' (línea $num_linea): ERROR - No se pudo crear"
        fi
        errores_creacion=true
    fi
    
done < "$ARCHIVO_USUARIOS"

# Mostrar resumen si se usa -i
if [[ "$MOSTRAR_INFO" == true ]]; then
    echo ""
    echo "Total de usuarios creados exitosamente: $usuarios_creados"
fi

# Salir con código de error apropiado
if [[ "$errores_sintaxis" == true ]]; then
    exit $ERROR_SINTAXIS_ARCHIVO
elif [[ "$errores_creacion" == true ]]; then
    exit $ERROR_OTRO
fi

exit 0
