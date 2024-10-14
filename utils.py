

def compute_dimensions(material: str, weight: float) -> dict:
    """
    Computes the estimated dimensions of a piece based on its material and weight.

    Args:
        material (str): The material of the piece. Must be "steel", "wood", or "plastic".
        weight (float): The weight of the piece in kilograms.

    Returns:
        dict: A dictionary containing the estimated volume (in cubic meters) and the dimension (in meters).
    
    Raises:
        ValueError: If the material is not recognized or the weight is non-positive.
    """

    # Densities in kg/m³
    material_densities = {
        "steel": 7850,   # Density of steel
        "wood": 600,     # Density of wood (approximate, varies by type)
        "plastic": 950   # Density of plastic (approximate)
    }

    # Validate material and weight
    if material.lower() not in material_densities:
        raise ValueError("Material must be 'steel', 'wood', or 'plastic'.")
    if weight <= 0:
        raise ValueError("Weight must be a positive number.")

    # Get the density for the given material
    density = material_densities[material.lower()]

    # Calculate volume (in cubic meters)
    volume = weight / density

    # Calculate the dimension of one side of a cubic piece (in meters)
    dimension = volume ** (1/3)

    return {
        "volume_m3": round(volume, 6),  # Volume in cubic meters, rounded for readability
        "dimension_m": round(dimension, 6)  # Dimension (one side of a cube) in meters, rounded
    }