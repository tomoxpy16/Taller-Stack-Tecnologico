// Datos semilla para desarrollo y demo. Se ejecuta solo cuando el volumen de Mongo está vacío
// (para recargar: docker compose down -v && docker compose up -d).
// Los índices NO se crean aquí: los aplica el backend al arrancar (app/adapters/outbound/persistence/mongo/indexes.py).
//
// Estado que deja la semilla, pensado para mostrar el flujo completo en la sustentación:
//   - Luna, Michi, Kiwi, Toby: disponibles (se puede postular).
//   - Rocky: postulado, con 2 postulaciones pendientes (al aprobar una, la otra se cierra sola).
//   - Nala: adoptada, con una postulación aprobada y otra rechazada por auto-cierre.

const target = db.getSiblingDB(process.env.MONGO_INITDB_DATABASE || "adopciones");
const ahora = new Date();
const haceDias = (n) => new Date(ahora.getTime() - n * 24 * 60 * 60 * 1000);
const foto = (seed, descripcion) => ({ url: `https://picsum.photos/seed/${seed}/600/400`, descripcion });

// --- Refugios ---------------------------------------------------------------
const refugioHuellitas = ObjectId("650000000000000000000001");
const refugioPatitas = ObjectId("650000000000000000000002");

target.refugios.insertMany([
  {
    _id: refugioHuellitas,
    nombre: "Fundación Huellitas",
    email: "contacto@huellitas.org",
    telefono: "+57 601 555 0101",
    direccion: { ciudad: "Bogotá", barrio: "Chapinero", linea: "Calle 45 # 13-20" },
    fecha_creacion: haceDias(120),
  },
  {
    _id: refugioPatitas,
    nombre: "Refugio Patitas Felices",
    email: "hola@patitasfelices.org",
    telefono: "+57 604 555 0202",
    direccion: { ciudad: "Medellín", barrio: "Laureles", linea: "Carrera 76 # 33-10" },
    fecha_creacion: haceDias(90),
  },
]);

// --- Adoptantes -------------------------------------------------------------
const ana = ObjectId("660000000000000000000001");
const carlos = ObjectId("660000000000000000000002");
const valentina = ObjectId("660000000000000000000003");

target.adoptantes.insertMany([
  { _id: ana, nombre: "Ana Gómez", email: "ana.gomez@mail.com", telefono: "+57 300 111 2233", ciudad: "Bogotá", fecha_registro: haceDias(30) },
  { _id: carlos, nombre: "Carlos Ruiz", email: "carlos.ruiz@mail.com", telefono: "+57 310 444 5566", ciudad: "Bogotá", fecha_registro: haceDias(20) },
  { _id: valentina, nombre: "Valentina Mora", email: "vale.mora@mail.com", telefono: "+57 320 777 8899", ciudad: "Medellín", fecha_registro: haceDias(10) },
]);

// --- Animales (documento embebido, campos variables por especie) -----------
const luna = ObjectId("670000000000000000000001");
const rocky = ObjectId("670000000000000000000002");
const michi = ObjectId("670000000000000000000003");
const nala = ObjectId("670000000000000000000004");
const kiwi = ObjectId("670000000000000000000005");
const toby = ObjectId("670000000000000000000006");

target.animales.insertMany([
  {
    _id: luna,
    refugio_id: refugioHuellitas,
    nombre: "Luna",
    especie: "perro",
    edad_meses: 24,
    sexo: "hembra",
    estado: "disponible",
    temperamento: ["juguetona", "sociable", "tranquila en casa"],
    salud: { vacunado: true, esterilizado: true, desparasitado: true, condiciones: [], ultima_revision: haceDias(15) },
    fotos: [foto("luna1", "Luna en el parque"), foto("luna2", "Luna descansando")],
    detalles_especie: { raza: "Mestiza", tamano: "mediano", nivel_energia: "alto", apto_apartamento: true },
    fecha_publicacion: haceDias(12),
  },
  {
    _id: rocky,
    refugio_id: refugioHuellitas,
    nombre: "Rocky",
    especie: "perro",
    edad_meses: 60,
    sexo: "macho",
    estado: "postulado",
    temperamento: ["leal", "protector"],
    salud: { vacunado: true, esterilizado: true, desparasitado: true, condiciones: ["displasia de cadera leve"], ultima_revision: haceDias(7) },
    fotos: [foto("rocky1", "Rocky mirando a la cámara")],
    detalles_especie: { raza: "Labrador", tamano: "grande", nivel_energia: "medio", apto_apartamento: false },
    fecha_publicacion: haceDias(25),
  },
  {
    _id: michi,
    refugio_id: refugioHuellitas,
    nombre: "Michi",
    especie: "gato",
    edad_meses: 8,
    sexo: "macho",
    estado: "disponible",
    temperamento: ["curioso", "independiente"],
    salud: { vacunado: true, esterilizado: false, desparasitado: true, condiciones: [], ultima_revision: haceDias(5) },
    fotos: [foto("michi1", "Michi en su cama"), foto("michi2", "Michi jugando")],
    detalles_especie: { raza: "Común europeo", pelaje: "atigrado", convive_con_perros: false, usa_arenero: true },
    fecha_publicacion: haceDias(6),
  },
  {
    _id: nala,
    refugio_id: refugioPatitas,
    nombre: "Nala",
    especie: "gato",
    edad_meses: 36,
    sexo: "hembra",
    estado: "adoptado",
    temperamento: ["cariñosa", "tranquila"],
    salud: { vacunado: true, esterilizado: true, desparasitado: true, condiciones: [], ultima_revision: haceDias(40) },
    fotos: [foto("nala1", "Nala al sol")],
    detalles_especie: { raza: "Siamés", pelaje: "corto", convive_con_perros: true, usa_arenero: true },
    fecha_publicacion: haceDias(60),
  },
  {
    _id: kiwi,
    refugio_id: refugioPatitas,
    nombre: "Kiwi",
    especie: "ave",
    edad_meses: 14,
    sexo: "macho",
    estado: "disponible",
    temperamento: ["parlanchín", "sociable"],
    salud: { vacunado: false, esterilizado: false, desparasitado: true, condiciones: [], ultima_revision: haceDias(20) },
    fotos: [foto("kiwi1", "Kiwi en su percha")],
    detalles_especie: { tipo: "Periquito australiano", habla: true, requiere_jaula: true, color_plumaje: "verde y amarillo" },
    fecha_publicacion: haceDias(9),
  },
  {
    _id: toby,
    refugio_id: refugioPatitas,
    nombre: "Toby",
    especie: "perro",
    edad_meses: 4,
    sexo: "macho",
    estado: "disponible",
    temperamento: ["enérgico", "juguetón"],
    salud: { vacunado: false, esterilizado: false, desparasitado: true, condiciones: ["pendiente segunda dosis de vacuna"], ultima_revision: haceDias(3) },
    fotos: [foto("toby1", "Toby cachorro"), foto("toby2", "Toby con su juguete")],
    detalles_especie: { raza: "Beagle", tamano: "pequeño", nivel_energia: "alto", apto_apartamento: true },
    fecha_publicacion: haceDias(2),
  },
]);

// --- Postulaciones ----------------------------------------------------------
target.postulaciones.insertMany([
  // Rocky: dos pendientes -> escenario para demostrar el auto-cierre al aprobar una.
  { adoptante_id: ana, animal_id: rocky, estado: "pendiente", mensaje: "Tengo casa con patio y experiencia con perros grandes.", fecha_postulacion: haceDias(4), fecha_resolucion: null, motivo_cierre: null },
  { adoptante_id: carlos, animal_id: rocky, estado: "pendiente", mensaje: "Me encantaría darle un hogar tranquilo.", fecha_postulacion: haceDias(2), fecha_resolucion: null, motivo_cierre: null },
  // Nala: ya adoptada, con el historial resultante del auto-cierre.
  { adoptante_id: valentina, animal_id: nala, estado: "aprobada", mensaje: "Vivo sola y trabajo desde casa.", fecha_postulacion: haceDias(30), fecha_resolucion: haceDias(25), motivo_cierre: null },
  { adoptante_id: ana, animal_id: nala, estado: "rechazada", mensaje: "Me gustan mucho los gatos siameses.", fecha_postulacion: haceDias(28), fecha_resolucion: haceDias(25), motivo_cierre: "cierre_automatico" },
]);

print(`Semilla cargada en '${target.getName()}': ${target.refugios.countDocuments()} refugios, ${target.adoptantes.countDocuments()} adoptantes, ${target.animales.countDocuments()} animales, ${target.postulaciones.countDocuments()} postulaciones.`);
