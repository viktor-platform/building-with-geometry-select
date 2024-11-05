import math
import numpy as np

import viktor as vkt


class Parametrization(vkt.ViktorParametrization):
    text1 = vkt.Text(
        "## Parametric Building with Geometry Select Features 👉\n"
        "1️⃣ **Define the general dimensions**"
    )
    width = vkt.NumberField('Width', min=0, default=30)
    length = vkt.NumberField('Length', min=0, default=30)
    number_floors = vkt.NumberField("Number of floors", variant='slider', min=5, max=40, default=10)

    text2 = vkt.Text("2️⃣ **Place columns and floors by clicking on the nodes**")
    add_columns = vkt.GeometryMultiSelectField("Add columns")
    add_floors = vkt.GeometryMultiSelectField("Add floors")

    text3 = vkt.Text("3️⃣ **Add balconies by selecting two nodes on a facade**")
    balconies = vkt.DynamicArray('Balconies')
    balconies.select = vkt.GeometryMultiSelectField('Select location', min_select=2, max_select=2)
    balconies.width = vkt.NumberField('Width', default=3)
    balconies.color = vkt.ColorField('Color', default=vkt.Color(128, 128, 128))


class Controller(vkt.ViktorController):
    label = "Parametric Building"
    parametrization = Parametrization

    @vkt.GeometryView("3D building", duration_guess=1, x_axis_to_right=True)
    def get_geometry(self, params, **kwargs):
        # Create nodes
        node_material = vkt.Material("Node", color=vkt.Color.viktor_blue())
        floor_height = 4
        no_nodes = 4
        node_radius = 0.5
        nodes = []
        for x in np.linspace(0, params.width, no_nodes):
            for y in np.linspace(0, params.length, no_nodes):
                for z in range(0, (params.number_floors+1)*floor_height, floor_height):
                    nodes.append(vkt.Sphere(centre_point=vkt.Point(x, y, z),
                                        radius=node_radius,
                                        material=node_material,
                                        identifier=f"{x}-{y}-{z}"))

        # Create beams
        b = 0.3  # Beam width
        p1 = vkt.Point(0, 0, floor_height)
        p2 = vkt.Point(params.width, 0, floor_height)
        p3 = vkt.Point(params.width, params.length, floor_height)
        p4 = vkt.Point(0, params.length, floor_height)

        b1 = vkt.RectangularExtrusion(b, b, vkt.Line(p1, p2))
        b2 = vkt.RectangularExtrusion(b, b, vkt.Line(p2, p3))
        b3 = vkt.RectangularExtrusion(b, b, vkt.Line(p3, p4))
        b4 = vkt.RectangularExtrusion(b, b, vkt.Line(p4, p1))

        beams = vkt.Group([b1, b2, b3, b4])

        # Create corner columns
        c1 = vkt.RectangularExtrusion(b, b, vkt.Line(vkt.Point(0, 0, 0), vkt.Point(0, 0, floor_height)))
        columns = vkt.BidirectionalPattern(c1, direction_1=[1, 0, 0], direction_2=[0, 1, 0], number_of_elements_1=2,
                                           number_of_elements_2=2, spacing_1=params.width, spacing_2=params.length)

        # Pattern to create complete building
        floor = vkt.Group([columns, beams])
        building = vkt.LinearPattern(floor, direction=[0, 0, 1], number_of_elements=params.number_floors, spacing=floor_height)

        total_height = floor_height*params.number_floors

        # Add columns based on selected nodes
        added_columns = []
        if params.add_columns:
            for c in params.add_columns:
                x = float(c.split("-")[0])
                y = float(c.split("-")[1])
                added_columns.append(vkt.RectangularExtrusion(b, b, vkt.Line(vkt.Point(x, y, 0), vkt.Point(x, y, total_height))))

        # Add floors based on selected nodes
        added_floors = []
        if params.add_floors:
            for f in params.add_floors:
                z = float(f.split("-")[-1])
                added_floors.append(vkt.SquareBeam(params.width, params.length, 0.3).translate((params.width/2, params.length/2, z)))

        # Add balconies based on selected nodes
        added_balconies = []
        balcony_thickness = 0.3
        if params.balconies:
            for count, b in enumerate(params.balconies):
                if b.select:
                    s = [float(i) for i in b.select[0].split("-")]
                    e = [float(i) for i in b.select[1].split("-")]

                    balcony = vkt.RectangularExtrusion(width=b.width, 
                                                       height=balcony_thickness, 
                                                       line=vkt.Line(vkt.Point(s[0], s[1], s[2]), vkt.Point(e[0], e[1], e[2])),
                                                       material=vkt.Material(color=b.color))

                    if s[0] == e[0] and s[2] == e[2]:  # Balcony in Y direction
                        if s[0] == 0:
                            balcony.translate([-b.width/2, 0, 0])
                        else:
                            balcony.translate([b.width/2, 0, 0])
                        added_balconies.append(balcony)
                    elif s[1] == e[1] and s[2] == e[2]:  # Balcony in X direction
                        balcony.rotate(angle=math.pi/2, direction=[1, 0, 0], point=s)
                        if s[1] == 0:
                            balcony.translate([0, -b.width/2, 0])
                        else:
                            balcony.translate([0, b.width/2, 0])
                        added_balconies.append(balcony)
                    else:
                        vkt.UserMessage.warning(f"Placement of balcony {count + 1} is invalid, it should be horizontal and connected to a single facade")

        return vkt.GeometryResult([vkt.Group(nodes), building, vkt.Group(added_columns), vkt.Group(added_floors), vkt.Group(added_balconies)])
    