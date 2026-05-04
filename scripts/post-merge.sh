#!/bin/bash
set -e

dotnet restore ORCA.Api/ORCA.Api.csproj
dotnet build ORCA.Api/ORCA.Api.csproj --configuration Release --no-restore
