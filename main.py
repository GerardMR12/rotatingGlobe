import sys
import numpy as np
from time import sleep
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

import pyproj
from pyproj import Geod

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from shapely.geometry import Polygon
from shapely.ops import transform

from PIL import Image
import imageio.v2 as imageio

# Display configuration
satellite_display = False # display the satellite image at its position (if centralized)
satellite_path = "resources\\satellite1.png"  # Path to the satellite image (will display if the marker is centered)
satellite_marker = "*"
vision_radius = 2000 # km
n_frames = 10
fps = 10
rotation_steps = np.linspace(0, 360, n_frames)

# Satellite position
satellite_data = (0, 70) # (longitude, latitude)

def create_elliptical_footprint(center_lon, center_lat, semi_major_km, semi_minor_km, angle_deg, num_points=100):
    geod = Geod(ellps="WGS84")
    
    # Generate points on an ellipse
    angles = np.linspace(0, 360, num_points)
    ellipse_points = []
    
    for theta in angles:
        # Calculate points on the ellipse using parametric equations
        # Adjust points based on the semi-major and semi-minor axes
        x = semi_major_km * np.cos(np.radians(theta))
        y = semi_minor_km * np.sin(np.radians(theta))
        
        # Rotate the ellipse by the specified angle
        x_rot = x * np.cos(np.radians(angle_deg)) - y * np.sin(np.radians(angle_deg))
        y_rot = x * np.sin(np.radians(angle_deg)) + y * np.cos(np.radians(angle_deg))
        
        # Calculate the lat/lon for the rotated points
        lon, lat, _ = geod.fwd(center_lon, center_lat, np.degrees(np.arctan2(y_rot, x_rot)), np.sqrt(x_rot**2 + y_rot**2) * 1000)
        ellipse_points.append((lon, lat))
    
    return Polygon(ellipse_points)

# Function to project and plot the elliptical footprint on the map
def plot_elliptical_footprint(ax, center_lon, center_lat, semi_major_km, semi_minor_km, angle_deg):
    # Create the elliptical footprint
    ellipse = create_elliptical_footprint(center_lon, center_lat, semi_major_km, semi_minor_km, angle_deg)
    
    # Define the transformation function from geographic to the projection
    transformer = pyproj.Transformer.from_crs("EPSG:4326", ax.projection.proj4_init, always_xy=True).transform
    
    # Transform the ellipse into the projection
    projected_ellipse = transform(transformer, ellipse)
    
    # Plot the transformed ellipse as a Polygon
    ax.add_patch(plt.Polygon(np.array(projected_ellipse.exterior.coords), facecolor="yellow", edgecolor="black", alpha=0.5))

# Define a function to create a geodesic circle (great-circle) around a point
def create_geodesic_circle(center_lon, center_lat, radius_km, num_points=100):
    # Initialize the geodesic calculator using WGS84 (standard Earth model)
    geod = Geod(ellps="WGS84")
    
    # Create an array of equally spaced angles around a circle
    angles = np.linspace(0, 360, num_points)
    
    # Calculate the lat/lon of points on the circle's perimeter
    circle_points = []
    for angle in angles:
        lon, lat, _ = geod.fwd(center_lon, center_lat, angle, radius_km * 1000)
        circle_points.append((lon, lat))
    
    return Polygon(circle_points)  # Return as a Shapely polygon

# Function to project and plot the geodesic circle on the map
def plot_geodesic_circle(ax, center_lon, center_lat, radius_km):
    # Create a geodesic circle (in lat/lon)
    geodesic_circle = create_geodesic_circle(center_lon, center_lat, radius_km)
    
    # Define the transformation function from geographic to the projection
    transformer = pyproj.Transformer.from_crs("EPSG:4326", ax.projection.proj4_init, always_xy=True).transform
    
    # Transform the geodesic circle into the projection (Orthographic)
    projected_circle = transform(transformer, geodesic_circle)
    
    # Plot the transformed circle as a Polygon
    ax.add_patch(plt.Polygon(np.array(projected_circle.exterior.coords), facecolor="yellow", edgecolor="black", alpha=0.5))

# Simulate Earth's rotation by changing the central longitude
def plot_frame(central_lon, central_lat, ax, satellite_data, ortho_proj):
    ax.set_global()  # Set global extent (full globe view)
    ax.coastlines()  # Draw coastlines

    # Add a colorful background image (stock image)
    ax.stock_img()

    # Add country borders with a thicker, more colorful line
    ax.add_feature(cfeature.BORDERS, edgecolor="black", linewidth=1.5)

    # Add coastlines with a thicker black line
    ax.add_feature(cfeature.COASTLINE, edgecolor="black", linewidth=1)

    # Plot the satellite position
    sat_lon, sat_lat = satellite_data

    if satellite_display and central_lon == satellite_data[0] and central_lat == satellite_data[1]:
        # Load your image (this will be used as the marker)
        img = Image.open(satellite_path)

        # Create an OffsetImage to place the image at the satellite position
        imagebox = OffsetImage(img, zoom=0.02)
        ab = AnnotationBbox(imagebox, satellite_data, frameon=False)
        ax.add_artist(ab)
    else:
        ax.plot(sat_lon, sat_lat, marker=satellite_marker, color="red", markersize=15, transform=ccrs.Geodetic())

    # Plot the geodesic circle around the satellite
    plot_geodesic_circle(ax, sat_lon, sat_lat, vision_radius)

    # Set the extent to ensure the circle is visible (optional, adjust as needed)
    ax.set_global()

if __name__ == "__main__":
    # Create list to store the frames for the GIF
    images = []

    # Generate frames
    for i, step in enumerate(rotation_steps):
        sys.stdout.write("\033[K")  # clear the line
        print(f"Generating frame {i+1}/{n_frames}...")

        # Maintain one line of output
        sys.stdout.write("\033[F")  # move cursor up one line

        # Create a new figure with an Orthographic projection
        fig = plt.figure(figsize=(10, 10))
        orto_proj = ccrs.Orthographic(central_longitude=step, central_latitude=step/4)
        ax = fig.subplots(subplot_kw={"projection": orto_proj})

        # Plot Earth
        plot_frame(step, step/4, ax, satellite_data, orto_proj)
        
        # Save frame as an image file
        filename = f"frames/frame_{int(step)}.png"
        plt.savefig(filename, bbox_inches="tight")

        sleep(0.01)  # Add a small delay to allow the image to save
        
        # Read the image and append it to the images list
        images.append(imageio.imread(filename))
        
        plt.close()  # Close the plot to avoid display in notebook

    # Create GIF from the frames
    imageio.mimsave("earth_rotation.gif", images, fps=fps)

    # Move cursor down and print message
    sys.stdout.write("\n")
    print("GIF saved as earth_rotation.gif")