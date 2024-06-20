import math

import numpy as np
from viktor.parametrization import ViktorParametrization, NumberField, ColorField, Text, GeometrySelectField, \
    GeometryMultiSelectField, DynamicArray
from viktor import ViktorController, UserMessage
from viktor.geometry import SquareBeam, Material, Color, Group, LinearPattern, Point, RectangularExtrusion, Line, \
    BidirectionalPattern, Sphere
from viktor.views import GeometryView, GeometryResult


class Parametrization(ViktorParametrization):
    text1 = Text(
        "## Parametric Building with Geometry Select Features 👉\n"
        "1️⃣ **Define the general dimensions**"
    )
    width = NumberField('Width', min=0, default=30)
    length = NumberField('Length', min=0, default=30)
    number_floors = NumberField("Number of floors", variant='slider', min=5, max=40, default=10)

    text2 = Text("2️⃣ **Place columns and floors by clicking on the nodes**")
    add_columns = GeometryMultiSelectField("Add columns")
    add_floors = GeometryMultiSelectField("Add floors")

    text3 = Text("3️⃣ **Add balconies by selecting two nodes on a facade**")
    balconies = DynamicArray('Balconies')
    balconies.select = GeometryMultiSelectField('Select location', min_select=2, max_select=2)
    balconies.width = NumberField('Width', default=3)
    balconies.color = ColorField('Color', default=Color(128, 128, 128))


class Controller(ViktorController):
    label = "Parametric Building"
    parametrization = Parametrization

    @GeometryView("3D building", duration_guess=1, x_axis_to_right=True)
    def get_geometry(self, params, **kwargs):
        # Create nodes
        node_material = Material("Node", color=Color.viktor_blue())
        floor_height = 4
        no_nodes = 4
        node_radius = 0.5
        nodes = []
        for x in np.linspace(0, params.width, no_nodes):
            for y in np.linspace(0, params.length, no_nodes):
                for z in range(0, (params.number_floors+1)*floor_height, floor_height):
                    nodes.append(Sphere(centre_point=Point(x, y, z),
                                        radius=node_radius,
                                        material=node_material,
                                        identifier=f"{x}-{y}-{z}"))

        # Create beams
        b = 0.3  # Beam width
        p1 = Point(0, 0, floor_height)
        p2 = Point(params.width, 0, floor_height)
        p3 = Point(params.width, params.length, floor_height)
        p4 = Point(0, params.length, floor_height)

        b1 = RectangularExtrusion(b, b, Line(p1, p2))
        b2 = RectangularExtrusion(b, b, Line(p2, p3))
        b3 = RectangularExtrusion(b, b, Line(p3, p4))
        b4 = RectangularExtrusion(b, b, Line(p4, p1))

        beams = Group([b1, b2, b3, b4])

        # Create corner columns
        c1 = RectangularExtrusion(b, b, Line(Point(0, 0, 0), Point(0, 0, floor_height)))
        columns = BidirectionalPattern(c1, direction_1=[1, 0, 0], direction_2=[0, 1, 0], number_of_elements_1=2,
                                       number_of_elements_2=2, spacing_1=params.width, spacing_2=params.length)

        floor = Group([columns, beams])
        building = LinearPattern(floor, direction=[0, 0, 1], number_of_elements=params.number_floors, spacing=floor_height)

        total_height = floor_height*params.number_floors

        # Add columns based on selected nodes
        added_columns = []
        if params.add_columns:
            for c in params.add_columns:
                x = float(c.split("-")[0])
                y = float(c.split("-")[1])
                added_columns.append(RectangularExtrusion(b, b, Line(Point(x, y, 0), Point(x, y, total_height))))

        # Add floors based on selected nodes
        added_floors = []
        if params.add_floors:
            for f in params.add_floors:
                z = float(f.split("-")[-1])
                added_floors.append(SquareBeam(params.width, params.length, 0.3).translate((params.width/2, params.length/2, z)))

        # Add balconies based on selected nodes
        added_balconies = []
        balcony_thickness = 0.3
        if params.balconies:
            for count, b in enumerate(params.balconies):
                if b.select:
                    s = [float(i) for i in b.select[0].split("-")]
                    e = [float(i) for i in b.select[1].split("-")]

                    balcony = RectangularExtrusion(width=b.width,
                                                   height=balcony_thickness,
                                                   line=Line(Point(s[0], s[1], s[2]), Point(e[0], e[1], e[2])),
                                                   material=Material(color=b.color))

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
                        UserMessage.warning(f"Placement of balcony {count + 1} is invalid, it should be horizontal and connected to a single facade")

        return GeometryResult([Group(nodes), building, Group(added_columns), Group(added_floors), Group(added_balconies)])
    