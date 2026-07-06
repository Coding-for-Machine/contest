# apps/video/admin.py
import uuid
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.conf import settings
from unfold.admin import ModelAdmin
from unfold.decorators import display
from baseuser.utils.admin import BaseOwnerAdmin
from .models import Video


@admin.register(Video)
class VideoAdmin(BaseOwnerAdmin):
    """
    Video admin paneli - BaseOwnerAdmin dan meros oladi
    """
    
    list_display = (
        'video_preview',
        'thumbnail_preview',
        'duration_display',
        'hls_status_display',
        'owner_display',
    )
    
    list_filter = ('hls_url',)
    search_fields = ('id', 'duration', 'hls_url')
    list_per_page = 25
    ordering = ('-id',)
    
    readonly_fields = (
        'id',
        'hls_player_preview',
        'video_info_display',
    )
    
    fieldsets = (
        ("🎬 Video Ma'lumotlari", {
            'fields': (
                'id',
                ('video', 'thumbnail'),
                'duration',
            )
        }),
        ("📡 HLS Oqim Sozlamalari", {
            'fields': (
                'hls_url',
                'hls_player_preview',
            ),
            'classes': ('wide',),
            'description': 'HLS oqim faylini quyidagi pleyer orqali tekshirishingiz mumkin.'
        }),
        ("📊 Qo'shimcha Ma'lumotlar", {
            'fields': ('video_info_display',),
            'classes': ('collapse',),
        }),
        ("👤 Yaratuvchi", {
            'fields': ('owner',),
        }),
    )
    
    # ============================================================
    # DISPLAY METHODS
    # ============================================================
    
    @display(description="🎬 Video")
    def video_preview(self, obj):
        if obj.video:
            return format_html(
                '<video width="120" height="68" controls style="border-radius: 8px; border: 1px solid #e2e8f0; background: #000;">'
                '<source src="{}" type="video/mp4">'
                'Brauzeringiz video playerini qo\'llamaydi.'
                '</video>',
                obj.video.url
            )
        return format_html(
            '<span style="color: #94a3b8; font-size: 13px;">📹 Video yo\'q</span>'
        )
    video_preview.short_description = "Video"
    
    @display(description="🖼️ Muqova")
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="width: 80px; height: 50px; object-fit: cover; '
                'border-radius: 8px; border: 1px solid #e2e8f0;" />',
                obj.thumbnail.url
            )
        return format_html(
            '<span style="color: #94a3b8; font-size: 13px;">🖼️ Yo\'q</span>'
        )
    thumbnail_preview.short_description = "Muqova"
    
    @display(description="⏱️ Davomiylik")
    def duration_display(self, obj):
        if obj.duration:
            return format_html(
                '<span style="background: #f1f5f9; padding: 2px 12px; '
                'border-radius: 20px; font-size: 12px; dark:bg-zinc-700;">⏱️ {}</span>',
                obj.duration
            )
        return "—"
    duration_display.short_description = "Davomiylik"
    
    @display(description="📡 HLS Holati")
    def hls_status_display(self, obj):
        if obj.hls_url:
            return format_html(
                '<span style="background: #22c55e; color: white; padding: 2px 12px; '
                'border-radius: 20px; font-size: 12px;">✅ Tayyor</span>'
            )
        return format_html(
            '<span style="background: #f59e0b; color: white; padding: 2px 12px; '
            'border-radius: 20px; font-size: 12px;">⏳ Tayyorlanmoqda</span>'
        )
    hls_status_display.short_description = "HLS Holati"
    
    @display(description="👤 Yaratuvchi")
    def owner_display(self, obj):
        if obj.owner:
            name = obj.owner.get_full_name() or obj.owner.username
            return format_html(
                '<span style="font-weight: 500;">{}</span>',
                name
            )
        return "—"
    owner_display.short_description = "Yaratuvchi"
    
    # ============================================================
    # VIDEO INFO DISPLAY
    # ============================================================
    
    def video_info_display(self, obj):
        info = []
        info.append(f"<strong>📌 ID:</strong> {obj.id}")
        
        if obj.video:
            info.append(f"<strong>📹 Video fayl:</strong> {obj.video.name}")
            try:
                size = obj.video.size
                if size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                info.append(f"<strong>📦 Hajmi:</strong> {size_str}")
            except:
                pass
        
        if obj.thumbnail:
            info.append(f"<strong>🖼️ Muqova:</strong> {obj.thumbnail.name}")
        
        if obj.hls_url:
            info.append(f"<strong>📡 HLS URL:</strong> <code style='background:#f1f5f9;padding:2px 8px;border-radius:4px;'>{obj.hls_url}</code>")
        
        return format_html(
            '<div style="background: #f8fafc; padding: 12px 16px; border-radius: 8px; '
            'border: 1px solid #e2e8f0; dark:bg-zinc-800 dark:border-zinc-700; '
            'font-size: 13px; color: #475569; dark:text-zinc-300; line-height: 1.8;">'
            '{}'
            '</div>',
            '<br>'.join(info)
        )
    video_info_display.short_description = "📊 Video Ma'lumotlari"
    
    # ============================================================
    # HLS PLAYER PREVIEW - TO'LIQ VERSIYA
    # ============================================================
    

    def hls_player_preview(self, obj):
        """
        HLS oqim faylini admin panelda pleyer orqali tekshirish
        (To'liq optimallashtirilgan versiya)
        """
        hls_path = obj.hls_url
        
        if not hls_path:
            return format_html(
                '<div style="padding: 20px; background: #fef3c7; border-radius: 12px; '
                'border: 1px solid #fcd34d; color: #78350f;">'
                '⚠️ HLS oqim fayli hali yaratilmagan.'
                '</div>'
            )
        
        # URL larni to'g'rilash
        if not hls_path.startswith(('/', 'http://', 'https://')):
            hls_path = f'/{hls_path}' if not hls_path.startswith('/') else hls_path
        
        thumbnail_url = obj.thumbnail.url if obj.thumbnail else ''
        video_id_str = str(obj.id).replace('-', '')
        
        # Xavfsizlik uchun URL larni tekshirish
        import re
        if not re.match(r'^[a-zA-Z0-9\-_/:.?&=]+$', hls_path.replace('http://', '').replace('https://', '')):
            return format_html(
                '<div style="padding: 20px; background: #fee2e2; border-radius: 12px; '
                'border: 1px solid #fecaca; color: #991b1b;">'
                '❌ Xavfli URL formati aniqlandi.'
                '</div>'
            )
        
        return format_html(
            '''
            <!-- Video.js CSS -->
            <link href="https://cdnjs.cloudflare.com/ajax/libs/video.js/7.20.3/video-js.min.css" rel="stylesheet" />
            
            <style>
                /* Global Wrapper */
                .hls-player-wrapper-{video_id} {{
                    position: relative;
                    width: 100%;
                    max-width: 100%;
                    margin: 0 auto;
                    background: #000;
                    border-radius: 12px;
                    overflow: hidden;
                    border: 1px solid #e2e8f0;
                    aspect-ratio: 16 / 9 !important;
                }}
                
                @media (min-width: 768px) {{
                    .hls-player-wrapper-{video_id} {{
                        max-width: 800px;
                    }}
                }}
                
                /* Video.js pleyerini wrapper ichiga majburlab mixlash */
                .hls-player-wrapper-{video_id} .video-js {{
                    width: 100% !important;
                    height: 100% !important;
                    position: absolute !important;
                    top: 0 !important;
                    left: 0 !important;
                    background: #000;
                }}
                
                /* Video elementining o'zini pleyer ichida buzilmasligini ta'minlash */
                .hls-player-wrapper-{video_id} .video-js video {{
                    width: 100% !important;
                    height: 100% !important;
                    object-fit: contain !important;
                    background: #000;
                }}
                
                .hls-player-wrapper-{video_id} .vjs-poster {{
                    background-size: contain !important;
                    background-color: #000 !important;
                }}
                
                .hls-player-wrapper-{video_id} .vjs-big-play-button {{
                    position: absolute !important;
                    top: 50% !important;
                    left: 50% !important;
                    transform: translate(-50%, -50%) !important;
                    z-index: 2 !important;
                }}
                
                /* Loading animatsiyasi */
                .hls-loading-{video_id} {{
                    display: none;
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    color: white;
                    font-size: 14px;
                    z-index: 1;
                    background: rgba(0,0,0,0.7);
                    padding: 10px 20px;
                    border-radius: 8px;
                }}
                
                .hls-loading-{video_id}.active {{
                    display: block;
                }}
            </style>
            
            <div style="margin-top: 8px;">
                <!-- Player Wrapper -->
                <div class="hls-player-wrapper-{video_id}">
                    <div class="hls-loading-{video_id}" id="hls-loading-{video_id}">
                        ⏳ Yuklanmoqda...
                    </div>
                    
                    <video id="hls-player-{video_id}" 
                        class="video-js vjs-big-play-centered vjs-default-skin" 
                        controls 
                        preload="auto"
                        poster="{poster_url}"
                        playsinline
                        crossorigin="anonymous">
                        <source src="{hls_url}" type="application/x-mpegURL">
                        <p class="vjs-no-js">Brauzeringiz videoni qo'llamaydi.</p>
                    </video>
                </div>
                
                <!-- HLS ma'lumotlari -->
                <div style="margin-top: 12px; padding: 12px 16px; background: #f8fafc; border-radius: 8px; 
                            border: 1px solid #e2e8f0; font-size: 13px; color: #475569;">
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <strong>📡 Oqim manzili:</strong>
                        <code style="background: #e2e8f0; padding: 4px 8px; border-radius: 4px; font-size: 12px; 
                                    word-break: break-all; flex: 1; color: #0f172a;">
                            {hls_url}
                        </code>
                    </div>
                    
                    <div style="margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap;">
                        <button type="button" onclick="testHLS('{video_id}', '{hls_url}')" 
                                style="display: inline-flex; align-items: center; gap: 4px; padding: 6px 14px; 
                                    background: #22c55e; color: white; border-radius: 6px; border: none; 
                                    font-size: 12px; cursor: pointer; transition: all 0.2s;">
                            ✅ Tekshirish
                        </button>
                        <button type="button" onclick="copyHLS('{video_id}', '{hls_url}')" 
                                style="display: inline-flex; align-items: center; gap: 4px; padding: 6px 14px; 
                                    background: #8b5cf6; color: white; border-radius: 6px; border: none; 
                                    font-size: 12px; cursor: pointer; transition: all 0.2s;">
                            📋 Nusxalash
                        </button>
                        <a href="{hls_url}" target="_blank" rel="noopener noreferrer"
                            style="display: inline-flex; align-items: center; gap: 4px; padding: 6px 14px; 
                                background: #3b82f6; color: white; border-radius: 6px; text-decoration: none; 
                                font-size: 12px;">
                            🔗 Ochish
                        </a>
                        <button type="button" onclick="reloadHLS('{video_id}')" 
                                style="display: inline-flex; align-items: center; gap: 4px; padding: 6px 14px; 
                                    background: #f59e0b; color: white; border-radius: 6px; border: none; 
                                    font-size: 12px; cursor: pointer; transition: all 0.2s;">
                            🔄 Qayta yuklash
                        </button>
                    </div>
                </div>
                
                <!-- Status xabarlari -->
                <div id="hls-status-{video_id}" style="margin-top: 8px; padding: 8px 12px; 
                                                    border-radius: 6px; font-size: 12px; display: none;">
                </div>
                
                <!-- Xatolik xabari -->
                <div id="hls-error-{video_id}" style="display: none; margin-top: 8px; padding: 10px; 
                                                    background: #fee2e2; border-radius: 6px; 
                                                    border: 1px solid #fecaca; color: #991b1b; font-size: 13px;">
                    ⚠️ Video player yuklanmadi. Iltimos, internet aloqangizni tekshiring.
                </div>
            </div>
            
            <!-- Scripts -->
            <script src="https://cdnjs.cloudflare.com/ajax/libs/video.js/7.20.3/video.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/videojs-contrib-hls@5.15.0/dist/videojs-contrib-hls.min.js"></script>
            
            <script>
                (function() {{
                    'use strict';
                    
                    let player_{video_id} = null;
                    let isPlayerInitialized_{video_id} = false;
                    
                    // Playerni yuklash funksiyasi
                    function initPlayer_{video_id}() {{
                        if (isPlayerInitialized_{video_id}) return;
                        
                        try {{
                            const loadingEl = document.getElementById('hls-loading-{video_id}');
                            const errorEl = document.getElementById('hls-error-{video_id}');
                            
                            // Loading ni ko'rsatish
                            if (loadingEl) loadingEl.classList.add('active');
                            
                            // Avvalgi instanceni o'chirish
                            if (player_{video_id}) {{
                                try {{
                                    player_{video_id}.dispose();
                                }} catch(e) {{}}
                                player_{video_id} = null;
                            }}
                            
                            // Video.js konfiguratsiyasi
                            const config = {{
                                fluid: false,
                                responsive: true,
                                aspectRatio: '16:9',
                                playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
                                controlBar: {{
                                    volumePanel: {{
                                        inline: false
                                    }}
                                }},
                                html5: {{
                                    hls: {{
                                        enableLowInitialPlaylist: true,
                                        smoothQualityChange: true,
                                        overrideNative: true,
                                        debug: false
                                    }}
                                }},
                                autoplay: false,
                                muted: false,
                                poster: '{poster_url}'
                            }};
                            
                            // Player yaratish
                            player_{video_id} = videojs('hls-player-{video_id}', config, function() {{
                                isPlayerInitialized_{video_id} = true;
                                
                                // Loading ni yashirish
                                if (loadingEl) loadingEl.classList.remove('active');
                                
                                // Xatoliklarni ushlash
                                this.on('error', function() {{
                                    showStatus_{video_id}('❌ Video yuklanmadi. Fayl mavjud emas yoki format noto\'g\'ri.', 'error');
                                }});
                                
                                this.on('loadedmetadata', function() {{
                                    showStatus_{video_id}('✅ Video muvaffaqiyatli yuklandi!', 'success');
                                }});
                                
                                console.log('✅ HLS player initialized for video {video_id}');
                            }});
                            
                        }} catch(e) {{
                            console.error('❌ Video.js error:', e);
                            const errorEl = document.getElementById('hls-error-{video_id}');
                            if (errorEl) errorEl.style.display = 'block';
                            
                            const loadingEl = document.getElementById('hls-loading-{video_id}');
                            if (loadingEl) loadingEl.classList.remove('active');
                        }}
                    }}
                    
                    // Status ko'rsatish funksiyasi
                    function showStatus_{video_id}(message, type) {{
                        const statusEl = document.getElementById('hls-status-{video_id}');
                        if (!statusEl) return;
                        
                        statusEl.style.display = 'block';
                        
                        if (type === 'success') {{
                            statusEl.style.background = '#dcfce7';
                            statusEl.style.color = '#15803d';
                        }} else if (type === 'error') {{
                            statusEl.style.background = '#fee2e2';
                            statusEl.style.color = '#b91c1c';
                        }} else {{
                            statusEl.style.background = '#e0f2fe';
                            statusEl.style.color = '#0369a1';
                        }}
                        
                        statusEl.innerText = message;
                        
                        // 5 soniyadan keyin avtomatik yashirish
                        if (type !== 'error') {{
                            clearTimeout(window.statusTimeout_{video_id});
                            window.statusTimeout_{video_id} = setTimeout(() => {{
                                statusEl.style.display = 'none';
                            }}, 5000);
                        }}
                    }}
                    
                    // HLS ni test qilish
                    window.testHLS = function(videoId, hlsUrl) {{
                        const statusEl = document.getElementById('hls-status-' + videoId);
                        if (!statusEl) return;
                        
                        statusEl.style.display = 'block';
                        statusEl.style.background = '#e0f2fe';
                        statusEl.style.color = '#0369a1';
                        statusEl.innerText = '⏳ Oqim tekshirilmoqda...';
                        
                        fetch(hlsUrl, {{ 
                            method: 'HEAD',
                            mode: 'cors',
                            cache: 'no-cache',
                            headers: {{
                                'Accept': 'application/vnd.apple.mpegurl'
                            }}
                        }})
                        .then(res => {{
                            if (res.ok) {{
                                showStatus_{video_id}('✅ Oqim fayli faol va ulanish muvaffaqiyatli!', 'success');
                            }} else {{
                                throw new Error('HTTP ' + res.status);
                            }}
                        }})
                        .catch(err => {{
                            console.error('Test error:', err);
                            showStatus_{video_id}('❌ Oqim fayliga ulanib boʻlmadi. Manzilni tekshiring: ' + err.message, 'error');
                        }});
                    }};
                    
                    // HLS ni nusxalash
                    window.copyHLS = function(videoId, hlsUrl) {{
                        if (navigator.clipboard && navigator.clipboard.writeText) {{
                            navigator.clipboard.writeText(hlsUrl).then(() => {{
                                showStatus_{video_id}('📋 Oqim manzili buferga nusxalandi!', 'success');
                            }}).catch(() => {{
                                // Fallback method
                                fallbackCopyHLS(videoId, hlsUrl);
                            }});
                        }} else {{
                            fallbackCopyHLS(videoId, hlsUrl);
                        }}
                    }};
                    
                    // Fallback nusxalash
                    function fallbackCopyHLS(videoId, hlsUrl) {{
                        try {{
                            const textarea = document.createElement('textarea');
                            textarea.value = hlsUrl;
                            textarea.style.position = 'fixed';
                            textarea.style.opacity = '0';
                            document.body.appendChild(textarea);
                            textarea.select();
                            document.execCommand('copy');
                            document.body.removeChild(textarea);
                            showStatus_{video_id}('📋 Oqim manzili buferga nusxalandi!', 'success');
                        }} catch(e) {{
                            showStatus_{video_id}('❌ Nusxalash amalga oshmadi. Qo\'lda nusxalang.', 'error');
                        }}
                    }}
                    
                    // HLS ni qayta yuklash
                    window.reloadHLS = function(videoId) {{
                        try {{
                            const player = videojs('hls-player-' + videoId);
                            if (player) {{
                                player.src({{ src: '{hls_url}', type: 'application/x-mpegURL' }});
                                player.load();
                                player.play();
                                showStatus_{video_id}('🔄 Oqim qayta yuklandi!', 'success');
                            }}
                        }} catch(e) {{
                            console.error('Reload error:', e);
                            showStatus_{video_id}('❌ Qayta yuklash amalga oshmadi.', 'error');
                        }}
                    }};
                    
                    // DOM tayyor bo'lganda playerni ishga tushirish
                    if (document.readyState === 'loading') {{
                        document.addEventListener('DOMContentLoaded', initPlayer_{video_id});
                    }} else {{
                        initPlayer_{video_id}();
                    }}
                    
                    // Sahifa yopilganda playerni tozalash
                    window.addEventListener('beforeunload', function() {{
                        try {{
                            if (player_{video_id}) {{
                                player_{video_id}.dispose();
                                player_{video_id} = null;
                            }}
                        }} catch(e) {{}}
                    }});
                    
                    // Sahifa ko'rinishi o'zgarganda video holatini saqlash
                    document.addEventListener('visibilitychange', function() {{
                        try {{
                            if (document.hidden && player_{video_id} && player_{video_id}.paused()) {{
                                // Video yashirilganda to'xtatilgan bo'lsa hech narsa qilma
                            }}
                        }} catch(e) {{}}
                    }});
                    
                }})();
            </script>
            ''',
            video_id=video_id_str,
            poster_url=thumbnail_url,
            hls_url=hls_path
        )
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        total_videos = Video.objects.count()
        with_hls = Video.objects.filter(hls_url__isnull=False).exclude(hls_url='').count()
        without_hls = Video.objects.filter(Q(hls_url__isnull=True) | Q(hls_url='')).count()
        with_thumbnail = Video.objects.filter(thumbnail__isnull=False).count()
        
        extra_context.update({
            'total_videos': total_videos,
            'with_hls': with_hls,
            'without_hls': without_hls,
            'with_thumbnail': with_thumbnail,
        })
        
        return super().changelist_view(request, extra_context=extra_context)