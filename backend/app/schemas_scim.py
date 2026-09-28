"""
SCIM 2.0 Pydantic schemas according to RFC 7643 and RFC 7644.
"""
from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field


class SCIMName(BaseModel):
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None
    middleName: Optional[str] = None


class SCIMEmail(BaseModel):
    value: str
    type: Optional[str] = "work"
    primary: Optional[bool] = True


class SCIMMeta(BaseModel):
    resourceType: str
    created: Optional[str] = None
    lastModified: Optional[str] = None
    location: Optional[str] = None
    version: Optional[str] = None


class SCIMUserCreate(BaseModel):
    schemas: Optional[List[str]] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    name: Optional[SCIMName] = None
    displayName: Optional[str] = None
    emails: Optional[List[SCIMEmail]] = None
    active: Optional[bool] = True
    externalId: Optional[str] = None
    title: Optional[str] = None
    userType: Optional[str] = None
    department: Optional[str] = None


class SCIMPatchOp(BaseModel):
    op: str  # add, replace, remove
    path: Optional[str] = None
    value: Any


class SCIMPatchRequest(BaseModel):
    schemas: Optional[List[str]] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    Operations: List[SCIMPatchOp]


class SCIMUserResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    id: str
    externalId: Optional[str] = None
    userName: str
    name: Optional[SCIMName] = None
    displayName: Optional[str] = None
    emails: Optional[List[SCIMEmail]] = None
    active: bool = True
    meta: SCIMMeta


class SCIMGroupMember(BaseModel):
    value: str  # User ID
    display: Optional[str] = None
    ref: Optional[str] = Field(None, alias="$ref")


class SCIMGroupResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    id: str
    displayName: str
    members: Optional[List[SCIMGroupMember]] = []
    meta: SCIMMeta


class SCIMListResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int = 20
    Resources: List[Any] = []


class SCIMErrorResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]
    detail: str
    status: str
    scimType: Optional[str] = None
