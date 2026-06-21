from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class DiscoSchema(BaseModel):
    categoria: str = Field(description="DISCO_INTERNO | LECTOR_OPTICO")
    tipo: Optional[str] = None
    interfaz: Optional[str] = None
    capacidad: Optional[str] = None
    modelo_crudo: Optional[str] = None


class EspecificacionSchema(BaseModel):
    so: Optional[str] = Field(None, description="Sistema operativo")
    so_version: Optional[str] = None
    cpu_modelo: Optional[str] = None
    ram_total_gb: Optional[float] = None
    gpu_modelo: Optional[str] = None
    discos: list[DiscoSchema] = Field(default_factory=list)


class ClienteSchema(BaseModel):
    nombre: str
    primer_apellido: str
    segundo_apellido: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    rut: Optional[str] = None
    tipo: str = "PERSONA"


class EquipoSchema(BaseModel):
    tipo: str
    marca: str
    modelo: str
    numero_serie: Optional[str] = None
    anio: Optional[int] = None


class DiagnosticoLookout(BaseModel):
    version_schema: str = Field(description="Versión del schema de exportación de Lookout")
    timestamp: str = Field(description="ISO 8601")
    archivo_origen: Optional[str] = None
    cliente: ClienteSchema
    equipo: EquipoSchema
    especificaciones: EspecificacionSchema
