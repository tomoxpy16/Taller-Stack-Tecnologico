"""Arranca el backend de Gustavo (adaptador en memoria) con datos de demostración.
No usa MongoDB: es solo para mostrar el flujo completo mientras el adaptador Mongo está pendiente."""
import sys, pathlib
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backend"))
from contextlib import asynccontextmanager
from app.main import app
from app.adapters.inbound.api.dependencies import get_repositorios
from app.domain.entities import Refugio, Animal, Adoptante, Postulacion, Direccion, Salud, Foto

def foto(emoji, bg):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><rect width="400" height="300" fill="{bg}"/><text x="200" y="185" font-size="140" text-anchor="middle">{emoji}</text></svg>'
    return Foto(url="data:image/svg+xml;utf8," + quote(svg))
hace = lambda d: datetime.now(timezone.utc) - timedelta(days=d)

r = get_repositorios()
g = lambda repo, e: repo._guardar_copia(e)
g(r.refugios, Refugio(id="r1", nombre="Huellitas Bogotá", email="contacto@huellitas.co", telefono="3001234567", direccion=Direccion(ciudad="Bogotá")))
g(r.refugios, Refugio(id="r2", nombre="Patitas Felices", email="hola@patitas.co", telefono="3109876543", direccion=Direccion(ciudad="Medellín")))
A = [
 ("a1","Luna","perro",24,"hembra",["juguetona","sociable","apta con niños"],Salud(vacunado=True,esterilizado=True,notas="Desparasitada en agosto."),[foto("🐕","#F6E7C8"),foto("🐶","#E7F0FA")],{"tamano":"mediano","raza":"mestiza"},"postulado",12,"r1"),
 ("a2","Michi","gato",8,"macho",["tranquilo","curioso"],Salud(vacunado=True,notas="Esterilización programada."),[foto("🐈","#E9E4F5")],{"pelaje":"corto"},"postulado",6,"r1"),
 ("a3","Kiwi","ave",12,"macho",["sociable","ruidoso"],Salud(notas="Revisión veterinaria al día."),[foto("🦜","#DFF3E4")],{"tipo":"periquito"},"disponible",3,"r2"),
 ("a4","Toby","perro",60,"macho",["calmado","leal"],Salud(vacunado=True,esterilizado=True),[foto("🐕‍🦺","#FBE3DC")],{"tamano":"grande","raza":"labrador mestizo"},"disponible",20,"r2"),
 ("a5","Nala","gato",36,"hembra",["independiente","cariñosa"],Salud(vacunado=True,esterilizado=True),[foto("🐱","#FDF1D6")],{"pelaje":"largo"},"adoptado",40,"r1"),
 ("a6","Coco","perro",4,"hembra",["juguetona","energética"],Salud(notas="Primera dosis de vacunas pendiente."),[foto("🐩","#E2F1F8")],{"tamano":"pequeño","raza":"mestiza"},"disponible",1,"r1"),
]
for (i,n,e,m,s,t,sa,f,d,est,dias,ref) in A:
    g(r.animales, Animal(id=i,refugio_id=ref,nombre=n,especie=e,edad_meses=m,sexo=s,temperamento=t,salud=sa,fotos=f,detalles_especie=d,estado=est,fecha_publicacion=hace(dias)))
for (i,n,em,tel,c) in [("d1","Ana Gómez","ana@correo.com","3011112222","Bogotá"),("d2","Carlos Ruiz","carlos@correo.com","3023334444","Bogotá"),("d3","Laura Pérez","laura@correo.com","3045556666","Chía")]:
    g(r.adoptantes, Adoptante(id=i,nombre=n,email=em,telefono=tel,ciudad=c))
for (i,msg,est,dias,an,ad) in [
 ("p1","Tengo patio grande y experiencia con perros medianos.","pendiente",1,"a1","d1"),
 ("p2","Trabajo desde casa y puedo dedicarle mucho tiempo.","pendiente",1,"a1","d2"),
 ("p5","Vivo con mi familia, tenemos patio y mucho amor para dar.","pendiente",0,"a1","d3"),
 ("p3","Siempre he tenido gatos, vivo en apartamento con malla.","pendiente",0,"a2","d3"),
 ("p4","Nos enamoramos de Nala en la jornada de adopción.","aprobada",15,"a5","d3")]:
    g(r.postulaciones, Postulacion(id=i,animal_id=an,adoptante_id=ad,mensaje=msg,estado=est,fecha_postulacion=hace(dias),fecha_resolucion=hace(10) if est=="aprobada" else None))

@asynccontextmanager
async def sin_mongo(_):
    yield
app.router.lifespan_context = sin_mongo
print("Backend de demo listo en http://localhost:8000 (datos en memoria)", flush=True)
import uvicorn
uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
