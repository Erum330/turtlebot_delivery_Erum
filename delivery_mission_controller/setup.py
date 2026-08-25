from setuptools import find_packages, setup

package_name = 'delivery_mission_controller'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Erum',
    maintainer_email='you@example.com',
    description='Action server driving a TurtleBot3 through a pickup, pause, and delivery mission.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'delivery_mission_node = delivery_mission_controller.delivery_mission_node:main',
        ],
    },
)
