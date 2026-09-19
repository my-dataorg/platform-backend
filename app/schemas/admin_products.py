from pydantic import BaseModel, ConfigDict, Field


class ProductFields(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    shortDescription: str = Field(min_length=1, max_length=2000)
    iconUrl: str = Field(default="", max_length=256)
    category: str = Field(min_length=1, max_length=64)
    tags: list[str] = Field(default_factory=list)
    featured: bool = False
    launchUrl: str = Field(min_length=1, max_length=256)
    status: str = "enabled"
    defaultPath: str = "/"
    embedEnabled: bool = True
    sortOrder: int = 0


class ProductCreate(ProductFields):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    shortDescription: str | None = Field(default=None, min_length=1, max_length=2000)
    iconUrl: str | None = Field(default=None, max_length=256)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    tags: list[str] | None = None
    featured: bool | None = None
    launchUrl: str | None = Field(default=None, min_length=1, max_length=256)
    status: str | None = None
    defaultPath: str | None = None
    embedEnabled: bool | None = None
    sortOrder: int | None = None


class ProductAdminOut(ProductFields):
    model_config = ConfigDict(from_attributes=True)
    slug: str


class ProductAdminList(BaseModel):
    items: list[ProductAdminOut]
