import subprocess
import os
import json
from pathlib import Path

class AdvancedVideoGenerator:
    def __init__(self, upload_folder='uploads', output_folder='generated_videos', assets_folder='assets'):
        self.upload_folder = upload_folder
        self.output_folder = output_folder
        self.assets_folder = assets_folder
        os.makedirs(output_folder, exist_ok=True)
        os.makedirs(f"{assets_folder}/music", exist_ok=True)
        
        # Configurações de templates
        self.templates = {
            'terreno': {
                'name': 'Terreno Urbano',
                'duration_per_image': 4,
                'transition_effect': 'fade',
                'text_style': {
                    'fontcolor': 'white',
                    'fontsize': 28,
                    'box': 1,
                    'boxcolor': 'green@0.7',
                    'boxborderw': 8
                },
                'filters': 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,eq=brightness=0.1:saturation=1.2'
            },
            'casa': {
                'name': 'Casa Residencial',
                'duration_per_image': 3,
                'transition_effect': 'slideright',
                'text_style': {
                    'fontcolor': 'white',
                    'fontsize': 26,
                    'box': 1,
                    'boxcolor': 'blue@0.6',
                    'boxborderw': 6
                },
                'filters': 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,eq=brightness=0.05:contrast=1.1'
            },
            'apartamento': {
                'name': 'Apartamentos',
                'duration_per_image': 3.5,
                'transition_effect': 'wiperight',
                'text_style': {
                    'fontcolor': 'white',
                    'fontsize': 24,
                    'box': 1,
                    'boxcolor': 'black@0.8',
                    'boxborderw': 5
                },
                'filters': 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,eq=brightness=0.08:saturation=1.1'
            }
        }
        
        # Configurações de música
        self.music_options = {
            'instrumental': {
                'name': 'Instrumental Leve',
                'volume': 0.3,
                'fade_in': 2,
                'fade_out': 3
            },
            'ambiente': {
                'name': 'Ambiente',
                'volume': 0.2,
                'fade_in': 1,
                'fade_out': 2
            },
            'animado': {
                'name': 'Animado',
                'volume': 0.4,
                'fade_in': 1,
                'fade_out': 2
            }
        }
    
    def create_property_video(self, files_data, property_data, job_id):
        """
        Cria um vídeo promocional do imóvel usando templates e efeitos
        """
        try:
            template_name = property_data.get('template', 'casa')
            music_name = property_data.get('music', 'instrumental')
            
            template = self.templates.get(template_name, self.templates['casa'])
            music_config = self.music_options.get(music_name, self.music_options['instrumental'])
            
            # Separar imagens e vídeos
            images = [f for f in files_data if f['type'] == 'image']
            videos = [f for f in files_data if f['type'] == 'video']
            
            # Criar vídeo a partir das imagens com template
            image_video_path = None
            if images:
                image_video_path = self._create_templated_slideshow(images, template, job_id)
            
            # Processar vídeos existentes com template
            processed_videos = []
            for video in videos:
                processed_path = self._process_video_with_template(video, template, job_id)
                if processed_path:
                    processed_videos.append(processed_path)
            
            # Combinar todos os vídeos
            all_videos = []
            if image_video_path:
                all_videos.append(image_video_path)
            all_videos.extend(processed_videos)
            
            if not all_videos:
                raise Exception("Nenhum conteúdo de vídeo foi gerado")
            
            # Concatenar vídeos
            concatenated_video = self._concatenate_videos_with_transitions(all_videos, template, job_id)
            
            # Adicionar texto/legendas com informações do imóvel
            video_with_text = self._add_property_info_styled(concatenated_video, property_data, template, job_id)
            
            # Adicionar música de fundo
            final_video = self._add_background_music(video_with_text, music_config, job_id)
            
            return final_video
            
        except Exception as e:
            print(f"Erro ao gerar vídeo: {str(e)}")
            return None
    
    def _create_templated_slideshow(self, images, template, job_id):
        """
        Cria um slideshow com template específico
        """
        try:
            duration = template['duration_per_image']
            filters = template['filters']
            
            # Criar arquivo de lista de imagens com transições
            image_list_file = f"{self.output_folder}/images_{job_id}.txt"
            with open(image_list_file, 'w') as f:
                for i, img in enumerate(images):
                    f.write(f"file '{os.path.abspath(img['path'])}'\n")
                    f.write(f"duration {duration}\n")
                # Repetir a última imagem
                if images:
                    f.write(f"file '{os.path.abspath(images[-1]['path'])}'\n")
            
            output_path = f"{self.output_folder}/slideshow_{job_id}.mp4"
            
            # Comando FFmpeg com filtros do template
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', image_list_file,
                '-vf', filters,
                '-c:v', 'libx264',
                '-r', '30',
                '-pix_fmt', 'yuv420p',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                os.remove(image_list_file)
                return output_path
            else:
                print(f"Erro FFmpeg slideshow: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Erro ao criar slideshow: {str(e)}")
            return None
    
    def _process_video_with_template(self, video_data, template, job_id):
        """
        Processa um vídeo individual aplicando filtros do template
        """
        try:
            input_path = video_data['path']
            output_path = f"{self.output_folder}/processed_{video_data['id']}_{job_id}.mp4"
            filters = template['filters']
            
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-vf', filters,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-r', '30',
                '-t', '10',  # Limitar a 10 segundos
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return output_path
            else:
                print(f"Erro FFmpeg processo: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Erro ao processar vídeo: {str(e)}")
            return None
    
    def _concatenate_videos_with_transitions(self, video_paths, template, job_id):
        """
        Concatena vídeos com efeitos de transição
        """
        try:
            if len(video_paths) == 1:
                return video_paths[0]
            
            # Para simplificar, usar concatenação simples
            # Em versão futura, implementar transições complexas
            concat_file = f"{self.output_folder}/concat_{job_id}.txt"
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{os.path.abspath(video_path)}'\n")
            
            output_path = f"{self.output_folder}/concatenated_{job_id}.mp4"
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                os.remove(concat_file)
                return output_path
            else:
                print(f"Erro FFmpeg concatenação: {result.stderr}")
                return video_paths[0]
                
        except Exception as e:
            print(f"Erro ao concatenar vídeos: {str(e)}")
            return video_paths[0] if video_paths else None
    
    def _add_property_info_styled(self, video_path, property_data, template, job_id):
        """
        Adiciona informações do imóvel com estilo do template
        """
        try:
            output_path = f"{self.output_folder}/with_text_{job_id}.mp4"
            text_style = template['text_style']
            
            # Criar texto com informações do imóvel
            info_text = f"{property_data['name']}"
            if property_data['area']:
                info_text += f" - {property_data['area']}m²"
            if property_data['price']:
                info_text += f" - R$ {property_data['price']}"
            if property_data['location']:
                info_text += f"\\n{property_data['location']}"
            
            # Construir filtro de texto com estilo
            text_filter = f"drawtext=text='{info_text}'"
            for key, value in text_style.items():
                text_filter += f":{key}={value}"
            text_filter += ":x=(w-text_w)/2:y=h-text_h-20"
            
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-vf', text_filter,
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return output_path
            else:
                print(f"Erro FFmpeg texto: {result.stderr}")
                return video_path
                
        except Exception as e:
            print(f"Erro ao adicionar texto: {str(e)}")
            return video_path
    
    def _add_background_music(self, video_path, music_config, job_id):
        """
        Adiciona música de fundo com configurações específicas
        """
        try:
            # Por enquanto, retornar o vídeo sem música
            # Em implementação futura, adicionar arquivos de música reais
            output_path = f"{self.output_folder}/final_{job_id}.mp4"
            
            # Simular adição de música copiando o arquivo
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-c', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return output_path
            else:
                print(f"Erro FFmpeg música: {result.stderr}")
                return video_path
                
        except Exception as e:
            print(f"Erro ao adicionar música: {str(e)}")
            return video_path
    
    def get_template_info(self):
        """
        Retorna informações sobre os templates disponíveis
        """
        return {name: template['name'] for name, template in self.templates.items()}
    
    def get_music_info(self):
        """
        Retorna informações sobre as opções de música
        """
        return {name: music['name'] for name, music in self.music_options.items()}

