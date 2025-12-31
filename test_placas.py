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
        try:
            # Espera máximo 5 segundos por el popup
            wait = WebDriverWait(self.driver, 5)
            # Ajusta estos selectores según la página específica
            popup_close = wait.until(EC.element_to_be_clickable((By.XPATH, "(//span[@class='modal-info-close'])[1]")))
            popup_close.click()
            print("✓ Popup cerrado")
            time.sleep(2)
        except Exception as e:
            print("No se encontró popup o ya estaba cerrado")
    
    def buscar_placa(self, placa):
        """
        Busca una placa en la página
        
        Args:
            placa: Número de placa a buscar
            
        Returns:
            dict con placa y resultado (Sí/No)
        """
        try:
            # Buscar el campo de entrada - ajusta el selector según tu página
            input_campo = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "txtBusqueda"))
                # Alternativas comunes:
                # (By.NAME, "placa")
                # (By.XPATH, "//input[@type='text']")
            )
            
            # Limpiar campo y escribir placa
            input_campo.clear()
            input_campo.send_keys(placa)
            input_campo.send_keys(Keys.RETURN)
            
            # Esperar resultados
            time.sleep(3)  # Ajusta según necesidad
            
            # Buscar en el resultado - ajusta según la palabra que indique infracción
            page_text = self.driver.page_source.lower()
            
            # Palabras que indican infracción (personaliza según tu caso)
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
            print(f"Error al procesar placa {placa}: {str(e)}")
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
                
                # Pausa entre consultas para no saturar el servidor
                time.sleep(2)
            
            print("\n✓ Procesamiento completado")
            
        finally:
            self.driver.quit()
            print("Navegador cerrado")
    
    def guardar_resultados(self, archivo_salida='resultados_infracciones.csv'):
        """Guarda los resultados en un archivo CSV"""
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
    URL_CONSULTA = "https://www.fcm.org.co/simit/#/home-public"  # Cambia por la URL real
    ARCHIVO_ENTRADA = "C:/Users/oscar/OneDrive/Documents/FT-HQ-C&P-18 Control de Infracciones de Tránsito.xlsx"  # Tu archivo con las placas
    COLUMNA_PLACAS = "Placa"  # Nombre de la columna con las placas
    ARCHIVO_SALIDA = "resultados_infracciones.csv"
    
    # Crear instancia y ejecutar
    checker = InfractionChecker(URL_CONSULTA, ARCHIVO_ENTRADA, COLUMNA_PLACAS)
    checker.procesar_todas_placas()
    checker.guardar_resultados(ARCHIVO_SALIDA)