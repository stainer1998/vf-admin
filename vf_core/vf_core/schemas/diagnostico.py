from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class CampoManual(BaseModel):
    valor: str
    fuente: str = "manual"


class ClienteSchema(BaseModel):
    tipo: str = "persona"
    nombre: CampoManual
    primer_apellido: CampoManual
    segundo_apellido: Optional[CampoManual] = None
    telefono: Optional[CampoManual] = None
    email: Optional[str] = None
    rut: Optional[str] = None
    razon_social: Optional[str] = None
    direccion: Optional[str] = None
    observaciones: Optional[str] = None


class EquipoMarcaSchema(BaseModel):
    tipo: str
    marca: CampoManual
    modelo: CampoManual
    numero_serie: Optional[CampoManual] = None
    ano: Optional[CampoManual] = None


class EquipoEnsambladoSchema(BaseModel):
    tipo: str = "desktop_ensamblado"
    identificador: Optional[CampoManual] = None
    placa_madre: Optional[CampoManual] = None
    fuente: Optional[CampoManual] = None
    gabinete: Optional[CampoManual] = None


class DiagnosticoLookout(BaseModel):
    version_schema: str = Field(description="Versión del schema de exportación de Lookout")
    herramienta: str = "lookout-cli"
    timestamp_inicio: str = Field(description="ISO 8601")
    timestamp_fin: Optional[str] = None
    tiene_permisos_admin: bool = False
    cliente: ClienteSchema
    equipo: dict[str, Any]
    specs: dict[str, Any] = Field(default_factory=dict)
    metadata_deteccion: Optional[dict[str, Any]] = None
