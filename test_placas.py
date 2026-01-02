import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

class InfractionChecker:
    def __init__(self, url, input_archivo, columna_placas):
        """
        Inicializa el verificador de infracciones
        
        Args:
            url: URL de la página de consulta
            input_archivo: Ruta del archivo de entrada (CSV o Excel)
            columna_placas: Nombre de la columna que contiene las placas
        """
        self.url = url
        self.input_archivo = input_archivo
        self.columna_placas = columna_placas
        self.driver = None
        self.resultados = []
        
    def iniciar_navegador(self):
        """Inicializa el navegador Chrome"""
        opciones = webdriver.ChromeOptions()
        # Descomentar la siguiente línea para ejecutar sin abrir ventana
        # opciones.add_argument('--headless')
        opciones.add_argument('--no-sandbox')
        opciones.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=opciones)
        self.driver.maximize_window()
        
    def cargar_placas(self):
        """Lee las placas desde el archivo de entrada"""
        if self.input_archivo.endswith('.csv'):
            df = pd.read_csv(self.input_archivo)
        elif self.input_archivo.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(self.input_archivo)
        else:
            raise ValueError("Formato de archivo no soportado. Use CSV o Excel")
        
        return df[self.columna_placas].dropna().tolist()
    
    def cerrar_popup(self):
        """Cierra el popup inicial si existe"""
        time.sleep(3)  # Espera inicial para que el popup cargue
        try:
            wait = WebDriverWait(self.driver, 5)
            popup_close = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "(//span[@class='modal-info-close'])[1]")
            ))
            popup_close.click()
            print("✓ Popup cerrado")
            #time.sleep(2)
        except Exception as e:
            print("No se encontró popup o ya estaba cerrado")
    
    def buscar_placa(self, placa, intentos_maximos=3):
        """
        Busca una placa en la página con sistema de reintentos
        
        Args:
            placa: Número de placa a buscar
            intentos_maximos: Número de reintentos en caso de error
            
        Returns:
            dict con placa y resultado (Sí/No)
        """
        for intento in range(intentos_maximos):
            try:
                # Buscar el campo de entrada con espera extendida
                input_campo = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.ID, "txtBusqueda"))
                )
                
                # Asegurar que el campo esté interactuable
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "txtBusqueda"))
                )
                
                # Limpiar campo y escribir placa
                input_campo.clear()
                time.sleep(0.5)
                input_campo.send_keys(placa)
                input_campo.send_keys(Keys.RETURN)
                
                # ESPERA EXPLÍCITA: Esperar hasta 20 segundos por el resultado
                WebDriverWait(self.driver, 20).until(
                    lambda driver: 
                        'comparendos y multas' in driver.page_source.lower() or
                        'no tienes comparendos ni multas' in driver.page_source.lower()
                )
                
                # Pequeña pausa adicional para asegurar carga completa
                time.sleep(1)
                
                # Buscar en el resultado
                page_text = self.driver.page_source.lower()
                
                # Palabras que indican infracción
                palabras_infraccion = ['comparendos y multas']
                palabras_sin_infraccion = ['no tienes comparendos ni multas']
                
                tiene_infraccion = any(palabra in page_text for palabra in palabras_infraccion)
                sin_infraccion = any(palabra in page_text for palabra in palabras_sin_infraccion)
                
                if sin_infraccion:
                    resultado = "No"
                elif tiene_infraccion:
                    resultado = "Sí"
                else:
                    resultado = "No determinado"
                
                print(f"Placa {placa}: {resultado}")
                
                return {
                    'Placa': placa,
                    'Tiene_Infraccion': resultado
                }
                
            except Exception as e:
                print(f"  ⚠ Intento {intento + 1}/{intentos_maximos} falló para {placa}: {str(e)}")
                
                if intento < intentos_maximos - 1:
                    # Aún quedan intentos
                    print(f"  → Reintentando en 5 segundos...")
                    time.sleep(5)
                    
                    # Intentar refrescar la página para estado limpio
                    try:
                        self.driver.refresh()
                        time.sleep(3)
                        self.cerrar_popup()
                    except:
                        pass
                else:
                    # Ya no quedan más intentos
                    print(f"  ✗ Error definitivo en placa {placa}")
                    return {
                        'Placa': placa,
                        'Tiene_Infraccion': 'Error'
                    }
    
    def procesar_todas_placas(self):
        """Procesa todas las placas del archivo"""
        print("Iniciando navegador...")
        self.iniciar_navegador()
        
        try:
            print(f"Cargando placas desde {self.input_archivo}...")
            placas = self.cargar_placas()
            print(f"Se encontraron {len(placas)} placas para procesar\n")
            
            # Abrir página y cerrar popup
            print(f"Accediendo a {self.url}...")
            self.driver.get(self.url)
            self.cerrar_popup()
            
            # Procesar cada placa
            for i, placa in enumerate(placas, 1):
                print(f"\n[{i}/{len(placas)}] Procesando placa: {placa}")
                resultado = self.buscar_placa(placa)
                self.resultados.append(resultado)
                
                # GUARDAR PROGRESO CADA 50 PLACAS
                if i % 50 == 0:
                    self.guardar_resultados('progreso_temporal.csv')
                    print(f"  💾 Progreso guardado: {i}/{len(placas)} placas")
                
                # REFRESCAR NAVEGADOR CADA 100 PLACAS (evita acumulación de memoria)
                if i % 100 == 0 and i < len(placas):
                    print(f"  🔄 Refrescando navegador para optimizar memoria...")
                    self.driver.refresh()
                    time.sleep(3)
                    self.cerrar_popup()
                    time.sleep(2)
                
                # Pausa entre consultas
                time.sleep(2)
            
            print("\n✓ Procesamiento completado")
            
        finally:
            self.driver.quit()
            print("Navegador cerrado")
    
    def guardar_resultados(self, archivo_salida='resultados_infracciones.csv'):
        """Guarda los resultados en un archivo CSV o Excel"""
        df_resultados = pd.DataFrame(self.resultados)
        
        if archivo_salida.endswith('.csv'):
            df_resultados.to_csv(archivo_salida, index=False, encoding='utf-8-sig')
        elif archivo_salida.endswith(('.xlsx', '.xls')):
            df_resultados.to_excel(archivo_salida, index=False)
        
        print(f"\n✓ Resultados guardados en: {archivo_salida}")
        print(f"\nResumen:")
        print(df_resultados['Tiene_Infraccion'].value_counts())

# Ejemplo de uso
if __name__ == "__main__":
    # Configuración
    URL_CONSULTA = "https://www.fcm.org.co/simit/#/home-public"
    ARCHIVO_ENTRADA = r"C:\Users\oscar\OneDrive\Documents\FT-HQ-C&P-18 Control de Infracciones de Tránsito.xlsx"
    COLUMNA_PLACAS = "Placa"
    ARCHIVO_SALIDA = "resultados_infracciones.xlsx"  # Puedes cambiar a .csv si prefieres
    
    # Crear instancia y ejecutar
    checker = InfractionChecker(URL_CONSULTA, ARCHIVO_ENTRADA, COLUMNA_PLACAS)
    checker.procesar_todas_placas()
    checker.guardar_resultados(ARCHIVO_SALIDA)