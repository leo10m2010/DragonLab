# Componentes nativos de DragonLab

La migración mantiene el motor Python como referencia y respaldo para comportamientos que todavía no se han portado. Compilar Rust no acredita la calibración de un carro ni su precisión en una partida nueva. Las regresiones deben conservar fuerza, alcance, colisiones, climas y redondeos antes de activar un componente.

## Compilar en Windows

Se requiere Rust con el target `x86_64-pc-windows-msvc`, las herramientas C++ de Visual Studio y un Windows SDK compatible. El script usa el toolchain ya instalado; no instala ni cambia la configuración de Rust, Visual Studio o Windows.

Desde PowerShell:

```powershell
./native/build_native.ps1
```

Cada crate debe incluir su `Cargo.lock` revisado. El build ejecuta Cargo con `--release --locked`, un target explícito y un directorio de salida común bajo `native/target`. Para usar exclusivamente las dependencias ya almacenadas:

```powershell
./native/build_native.ps1 -Offline
```

Se puede compilar solo un componente mediante `-Component Core` o `-Component Overlay`. Cargo puede descargar dependencias ausentes en el modo normal; `-Offline` las rechaza. El script no instala toolchains ni realiza cambios globales.

Los artefactos finales son `native/bin/dragonlab_core.dll` y `native/bin/dragonlab_overlay.dll`. `native-manifest.json` registra esquema, ABI, versión del programa, target, compilador, tamaño y SHA-256 de cada DLL presente. Si una DLL está en uso, el reemplazo puede fallar: el script no detiene procesos ni cierra Chrome. El build de un único componente conserva la otra DLL existente; para publicar una versión nueva se debe ejecutar el build de ambos y validar el conjunto.

No se debe copiar una DLL de arquitectura distinta al proceso Python. Una migración parcial conserva el runtime y bibliotecas del launcher actual, por lo que el ahorro de CPU no implica todavía un ahorro equivalente de tamaño o RAM.

## Reducir el paquete compatible

El inventario de la versión 0.18 encontró `PIL/_avif.cp312-win_amd64.pyd` con 7.909.168 bytes sin comprimir. El diálogo manual admite PNG, JPG/JPEG y BMP; las capturas del navegador usan PNG. `PIL.AvifImagePlugin` y `PIL._avif` son candidatos a exclusión del empaquetado si no se ofrece AVIF en otra función. Antes de aplicar esa exclusión deben comprobarse apertura de los formatos admitidos, capturas, miniaturas y arranque del ejecutable. La reducción del EXE debe medirse sobre el paquete nuevo: el tamaño bruto del codec no es su ahorro comprimido. Esta documentación no modifica las exclusiones de PyInstaller.

## Verificación

1. Ejecutar las pruebas Rust de cada crate con `cargo test --locked --manifest-path native/<crate>/Cargo.toml`.
2. Ejecutar las regresiones de integración contra el motor Python, incluyendo cancelación y rechazo de comportamientos no portados.
3. Medir lectura, cálculo y dibujo por separado. La demora del navegador o su consumo no desaparecen al cambiar el solver.
4. Verificar el manifiesto y las DLL incluidas en el ejecutable distribuido.

El overlay debe ser transparente, no recibir foco ni capturar clics, agrupar actualizaciones obsoletas y cerrar su hilo de mensajes. El motor debe admitir cancelación y devolver un resultado no soportado para usar el respaldo sin mezclar modelos.
