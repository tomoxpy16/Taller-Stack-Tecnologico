/** Datos semilla del modo mock (mismos que debería tener el seed de Mongo). */

const foto = (emoji, bg) =>
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><rect width="400" height="300" fill="${bg}"/><text x="200" y="185" font-size="140" text-anchor="middle">${emoji}</text></svg>`,
  )

export const refugios = [
  { id: 'r1', type: 'refugios', nombre: 'Huellitas Bogotá', ciudad: 'Bogotá', telefono: '3001234567', email: 'contacto@huellitas.co' },
  { id: 'r2', type: 'refugios', nombre: 'Patitas Felices', ciudad: 'Medellín', telefono: '3109876543', email: 'hola@patitas.co' },
]

const hace = (dias) => new Date(Date.now() - dias * 86400000).toISOString()

export const animals = [
  {
    id: 'a1', nombre: 'Luna', especie: 'perro', edadMeses: 24, sexo: 'hembra',
    temperamento: ['juguetona', 'sociable', 'apta con niños'],
    salud: { vacunado: true, esterilizado: true, notas: 'Desparasitada en agosto.' },
    fotos: [foto('🐕', '#F6E7C8'), foto('🐶', '#E7F0FA')],
    detallesEspecie: { tamano: 'mediano', raza: 'mestiza' },
    estado: 'postulado', publicadoEn: hace(12), refugioId: 'r1',
  },
  {
    id: 'a2', nombre: 'Michi', especie: 'gato', edadMeses: 8, sexo: 'macho',
    temperamento: ['tranquilo', 'curioso'],
    salud: { vacunado: true, esterilizado: false, notas: 'Esterilización programada.' },
    fotos: [foto('🐈', '#E9E4F5')],
    detallesEspecie: { pelaje: 'corto', convivenciaConPerros: true },
    estado: 'postulado', publicadoEn: hace(6), refugioId: 'r1',
  },
  {
    id: 'a3', nombre: 'Kiwi', especie: 'ave', edadMeses: 12, sexo: 'macho',
    temperamento: ['sociable', 'ruidoso'],
    salud: { vacunado: false, esterilizado: false, notas: 'Revisión veterinaria al día.' },
    fotos: [foto('🦜', '#DFF3E4')],
    detallesEspecie: { tipo: 'periquito', puedeHablar: false, requiereJaula: true },
    estado: 'disponible', publicadoEn: hace(3), refugioId: 'r2',
  },
  {
    id: 'a4', nombre: 'Toby', especie: 'perro', edadMeses: 60, sexo: 'macho',
    temperamento: ['calmado', 'leal'],
    salud: { vacunado: true, esterilizado: true, notas: '' },
    fotos: [foto('🐕‍🦺', '#FBE3DC')],
    detallesEspecie: { tamano: 'grande', raza: 'labrador mestizo' },
    estado: 'disponible', publicadoEn: hace(20), refugioId: 'r2',
  },
  {
    id: 'a5', nombre: 'Nala', especie: 'gato', edadMeses: 36, sexo: 'hembra',
    temperamento: ['independiente', 'cariñosa'],
    salud: { vacunado: true, esterilizado: true, notas: '' },
    fotos: [foto('🐱', '#FDF1D6')],
    detallesEspecie: { pelaje: 'largo', convivenciaConPerros: false },
    estado: 'adoptado', publicadoEn: hace(40), refugioId: 'r1',
  },
  {
    id: 'a6', nombre: 'Coco', especie: 'perro', edadMeses: 4, sexo: 'hembra',
    temperamento: ['juguetona', 'energética'],
    salud: { vacunado: false, esterilizado: false, notas: 'Primera dosis de vacunas pendiente.' },
    fotos: [foto('🐩', '#E2F1F8')],
    detallesEspecie: { tamano: 'pequeño', raza: 'mestiza' },
    estado: 'disponible', publicadoEn: hace(1), refugioId: 'r1',
  },
]

export const adoptantes = [
  { id: 'd1', nombre: 'Ana Gómez', email: 'ana@correo.com', telefono: '3011112222', ciudad: 'Bogotá' },
  { id: 'd2', nombre: 'Carlos Ruiz', email: 'carlos@correo.com', telefono: '3023334444', ciudad: 'Bogotá' },
  { id: 'd3', nombre: 'Laura Pérez', email: 'laura@correo.com', telefono: '3045556666', ciudad: 'Chía' },
]

export const postulaciones = [
  { id: 'p1', mensaje: 'Tengo patio grande y experiencia con perros medianos.', estado: 'pendiente', motivoCierre: null, creadaEn: hace(1), resueltaEn: null, animalId: 'a1', adoptanteId: 'd1' },
  { id: 'p2', mensaje: 'Trabajo desde casa y puedo dedicarle mucho tiempo.', estado: 'pendiente', motivoCierre: null, creadaEn: hace(1), resueltaEn: null, animalId: 'a1', adoptanteId: 'd2' },
  { id: 'p5', mensaje: 'Vivo con mi familia, tenemos patio y mucho amor para dar.', estado: 'pendiente', motivoCierre: null, creadaEn: hace(0), resueltaEn: null, animalId: 'a1', adoptanteId: 'd3' },
  { id: 'p3', mensaje: 'Siempre he tenido gatos, vivo en apartamento con malla.', estado: 'pendiente', motivoCierre: null, creadaEn: hace(0), resueltaEn: null, animalId: 'a2', adoptanteId: 'd3' },
  { id: 'p4', mensaje: 'Nos enamoramos de Nala en la jornada de adopción.', estado: 'aprobada', motivoCierre: null, creadaEn: hace(15), resueltaEn: hace(10), animalId: 'a5', adoptanteId: 'd3' },
]
