//! ISO-X 3D cinematic prototype.
//! IMPORTANT: this is an optional visual scene only. It does NOT collect
//! passwords or replace LightDM/PAM. Press Enter or wait ~9 seconds to close it.
use bevy::prelude::*;
use bevy::app::AppExit;
use std::time::Duration;

#[derive(Component)] struct LogoPart;
#[derive(Component)] struct OrbitParticle { phase: f32, radius: f32, speed: f32, height: f32 }
#[derive(Component)] struct Crystal;
#[derive(Resource)] struct SceneClock { remaining: Timer }

fn main() {
    App::new()
        .insert_resource(ClearColor(Color::srgb(0.025, 0.025, 0.045)))
        .insert_resource(GlobalAmbientLight { color: Color::srgb(0.10, 0.20, 0.28), brightness: 180.0, affects_lightmapped_meshes: false })
        .insert_resource(SceneClock { remaining: Timer::new(Duration::from_secs(9), TimerMode::Once) })
        .add_plugins(DefaultPlugins.set(AssetPlugin { file_path: "/usr/share/iso-x/cinematic-assets".into(), ..default() }).set(WindowPlugin {
            primary_window: Some(Window {
                title: "ISO-X | مشهد ترحيبي ثلاثي الأبعاد".to_string(),
                resolution: (1280, 720).into(),
                resizable: true,
                ..default()
            }),
            ..default()
        }))
        .add_systems(Startup, setup)
        .add_systems(Update, (animate_scene, exit_to_system_login))
        .run();
}

fn setup(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    asset_server: Res<AssetServer>,
) {
    commands.spawn((Camera3d::default(), Transform::from_xyz(0.0, 0.0, 13.0).looking_at(Vec3::ZERO, Vec3::Y)));
    commands.spawn((PointLight {
        intensity: 1900.0, range: 30.0, shadows_enabled: false,
        color: Color::srgb(0.0, 0.75, 1.0), ..default()
    }, Transform::from_xyz(4.0, 4.5, 7.0)));
    commands.spawn((PointLight {
        intensity: 1300.0, range: 25.0, shadows_enabled: false,
        color: Color::srgb(0.45, 0.10, 1.0), ..default()
    }, Transform::from_xyz(-5.0, -1.5, 4.0)));

    let cyan = materials.add(StandardMaterial {
        base_color: Color::srgb(0.0, 0.78, 0.91),
        emissive: LinearRgba::rgb(0.0, 0.65, 0.95), metallic: 0.82, perceptual_roughness: 0.22,
        ..default()
    });
    let purple = materials.add(StandardMaterial {
        base_color: Color::srgb(0.38, 0.22, 0.92),
        emissive: LinearRgba::rgb(0.22, 0.06, 0.75), metallic: 0.65, perceptual_roughness: 0.28,
        ..default()
    });
    let glass = materials.add(StandardMaterial {
        base_color: Color::srgba(0.045, 0.07, 0.13, 0.72),
        alpha_mode: AlphaMode::Blend, metallic: 0.22, perceptual_roughness: 0.18,
        ..default()
    });
    let dark = materials.add(StandardMaterial {
        base_color: Color::srgb(0.035, 0.04, 0.065), metallic: 0.65, perceptual_roughness: 0.32,
        ..default()
    });

    // Use the actual project dragon branding as a textured panel. The source PNG
    // is staged to /usr/share/iso-x/cinematic-assets/images by build-iso.sh.
    let dragon_image: Handle<Image> = asset_server.load("images/iso-x-dragon.png");
    let dragon_material = materials.add(StandardMaterial {
        base_color: Color::WHITE,
        base_color_texture: Some(dragon_image),
        unlit: true,
        ..default()
    });
    commands.spawn((
        Mesh3d(meshes.add(Rectangle::new(2.35, 2.35))),
        MeshMaterial3d(dragon_material),
        Transform::from_xyz(0.0, 0.78, 1.15),
    ));

    // Metallic floating glass-like panel; opacity varies by GPU renderer.
    commands.spawn((Mesh3d(meshes.add(Cuboid::new(8.2, 3.1, 0.18))), MeshMaterial3d(glass), Transform::from_xyz(0.0, -0.75, 0.25)));
    commands.spawn((Mesh3d(meshes.add(Cuboid::new(8.28, 3.18, 0.055))), MeshMaterial3d(cyan.clone()), Transform::from_xyz(0.0, -0.75, 0.12)));
    commands.spawn((Mesh3d(meshes.add(Cuboid::new(7.96, 2.86, 0.07))), MeshMaterial3d(dark), Transform::from_xyz(0.0, -0.75, 0.34)));

    // Six metallic bars form a hexagon, then a minimal angular twin-wing emblem.
    let hex_r = 1.27_f32;
    for i in 0..6 {
        let a = i as f32 * std::f32::consts::TAU / 6.0;
        let p = Vec3::new(a.cos() * hex_r, a.sin() * hex_r + 1.38, 0.75);
        let next_a = (i as f32 + 1.0) * std::f32::consts::TAU / 6.0;
        let p2 = Vec3::new(next_a.cos() * hex_r, next_a.sin() * hex_r + 1.38, 0.75);
        let d = p2 - p;
        commands.spawn((Mesh3d(meshes.add(Cuboid::new(d.length(), 0.075, 0.09))), MeshMaterial3d(cyan.clone()),
            Transform::from_translation((p + p2) / 2.0).with_rotation(Quat::from_rotation_z(d.y.atan2(d.x))), LogoPart));
    }
    let wing_bars = [
        (Vec3::new(-0.65, 1.62, 0.88), Vec3::new(-0.34, 0.32, 0.1), purple.clone()),
        (Vec3::new(-0.97, 1.45, 0.88), Vec3::new(-0.48, 0.22, 0.1), cyan.clone()),
        (Vec3::new(-0.55, 0.93, 0.88), Vec3::new(-0.45, 0.20, 0.1), purple.clone()),
        (Vec3::new(0.65, 1.62, 0.88), Vec3::new(-0.34, 0.32, 0.1), purple.clone()),
        (Vec3::new(0.97, 1.45, 0.88), Vec3::new(-0.48, 0.22, 0.1), cyan.clone()),
        (Vec3::new(0.55, 0.93, 0.88), Vec3::new(-0.45, 0.20, 0.1), purple.clone()),
        (Vec3::new(0.0, 1.5, 0.92), Vec3::new(0.11, 0.92, 0.1), cyan.clone()),
    ];
    for (pos, size, mat) in wing_bars {
        let rotation = if pos.x < 0.0 { 0.38 } else if pos.x > 0.0 { -0.38 } else { 0.0 };
        commands.spawn((Mesh3d(meshes.add(Cuboid::new(size.x.abs().max(0.1), size.y, size.z))), MeshMaterial3d(mat),
            Transform::from_translation(pos).with_rotation(Quat::from_rotation_z(rotation)), LogoPart));
    }

    // Twelve hovering crystals provide the glass-fragment motif without a heavy particle simulation.
    for i in 0..12 {
        let a = i as f32 * std::f32::consts::TAU / 12.0;
        let radius = 3.15 + (i % 3) as f32 * 0.32;
        let material = if i % 2 == 0 { cyan.clone() } else { purple.clone() };
        commands.spawn((Mesh3d(meshes.add(Cuboid::new(0.12, 0.22, 0.10))), MeshMaterial3d(material),
            Transform::from_xyz(a.cos() * radius, a.sin() * radius * 0.52 + 0.15, 1.0), Crystal));
    }
    let particle_mesh = meshes.add(Sphere::new(0.035).mesh().ico(2).expect("valid icosphere"));
    for i in 0..84 {
        let phase = i as f32 * 2.399_963_2;
        let radius = 2.0 + ((i * 17) % 43) as f32 * 0.075;
        let color = if i % 3 == 0 { cyan.clone() } else { purple.clone() };
        commands.spawn((Mesh3d(particle_mesh.clone()), MeshMaterial3d(color),
            Transform::from_xyz(phase.cos() * radius, phase.sin() * radius * 0.45, -0.3 + (i % 4) as f32 * 0.18),
            OrbitParticle { phase, radius, speed: 0.24 + (i % 7) as f32 * 0.035, height: 0.30 + (i % 5) as f32 * 0.10 }));
    }

    // 3D world-space typography. The name is visible as a world-space text object,
    // but Bevy Text2d is not extruded glyph geometry; true Arabic 3D extrusion remains a gap.
    let font: Handle<Font> = asset_server.load("fonts/NotoSansArabic-Regular.ttf");
    commands.spawn((Text2d::new("ISO-X"), TextFont { font: font.clone(), font_size: 58.0, ..default() },
        TextColor(Color::srgb(0.0, 0.88, 1.0)), Transform::from_xyz(0.0, 2.65, 1.8)));
    commands.spawn((Text2d::new("المطور: عبدالله لازم"), TextFont { font, font_size: 34.0, ..default() },
        TextColor(Color::srgb(0.84, 0.90, 1.0)), Transform::from_xyz(0.0, -1.12, 1.5)));
    commands.spawn((Text2d::new("مشهد ترحيبي بصري — المصادقة الحقيقية يديرها LightDM / PAM"),
        TextFont { font_size: 18.0, ..default() }, TextColor(Color::srgb(0.64, 0.72, 0.84)),
        Transform::from_xyz(0.0, -2.0, 1.7)));
    commands.spawn((Text2d::new("اضغط Enter للإغلاق والعودة إلى لوحة الترحيب"),
        TextFont { font_size: 21.0, ..default() }, TextColor(Color::srgb(1.0, 0.43, 0.0)),
        Transform::from_xyz(0.0, -2.45, 1.7)));
}

fn animate_scene(time: Res<Time>, mut logo: Query<&mut Transform, With<LogoPart>>,
                 mut particles: Query<(&mut Transform, &OrbitParticle)>, mut crystals: Query<&mut Transform, With<Crystal>>) {
    let t = time.elapsed_secs();
    for mut transform in &mut logo {
        transform.rotate_local_z(0.12 * time.delta_secs());
        transform.translation.z = 0.75 + 0.06 * (t * 1.8).sin();
    }
    for (mut transform, particle) in &mut particles {
        let a = particle.phase + t * particle.speed;
        transform.translation.x = a.cos() * particle.radius;
        transform.translation.y = a.sin() * particle.radius * 0.45 + particle.height * (t * 1.3 + particle.phase).sin();
    }
    for mut transform in &mut crystals {
        transform.rotate_local_z(0.25 * time.delta_secs());
        transform.rotate_local_x(0.12 * time.delta_secs());
    }
}

fn exit_to_system_login(time: Res<Time>, keys: Res<ButtonInput<KeyCode>>, mut exit: MessageWriter<AppExit>, mut clock: ResMut<SceneClock>) {
    clock.remaining.tick(time.delta());
    if keys.just_pressed(KeyCode::Enter) || keys.just_pressed(KeyCode::NumpadEnter) || clock.remaining.is_finished() {
        exit.write(AppExit::Success);
    }
}
