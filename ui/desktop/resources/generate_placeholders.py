#!/usr/bin/env python3
"""
Placeholder image generator for resources folder.
Run this script to create placeholder PNG images.
Replace these with your actual images later.
"""

try:
    from PIL import Image, ImageDraw
    import os
    
    resources_dir = os.path.dirname(__file__)
    
    # Create profile placeholder (48x48)
    profile_img = Image.new('RGBA', (48, 48), (79, 70, 229, 255))  # Indigo color
    draw = ImageDraw.Draw(profile_img)
    # Draw simple person icon
    draw.ellipse([12, 8, 36, 20], fill=(255, 255, 255, 255))  # Head
    draw.polygon([(12, 20), (36, 20), (32, 36), (16, 36)], fill=(255, 255, 255, 255))  # Body
    profile_img.save(os.path.join(resources_dir, 'profile.png'))
    print("✅ Created profile.png")
    
    # Create logo placeholder (lettering)
    logo_img = Image.new('RGBA', (40, 32), (79, 70, 229, 255))  # Indigo color
    draw = ImageDraw.Draw(logo_img)
    draw.text((8, 8), "AI", fill=(255, 255, 255, 255), font=None)
    logo_img.save(os.path.join(resources_dir, 'logo.png'))
    print("✅ Created logo.png")
    
except ImportError:
    print("❌ PIL not installed. Install with: pip install Pillow")
    print("📝 Manually add placeholder images instead:")
    print("   - profile.png (48x48)")
    print("   - logo.png (40x32+)")
except Exception as e:
    print(f"❌ Error: {e}")
