import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Annotation, AnnotationStatus, AnnotationType } from './annotation.entity';
import { CreateAnnotationDto, UpdateAnnotationDto } from './dto/create-annotation.dto';

@Injectable()
export class AnnotationService {
  constructor(
    @InjectRepository(Annotation)
    private annotationRepository: Repository<Annotation>,
  ) {}

  async create(dto: CreateAnnotationDto): Promise<Annotation> {
    const annotation = this.annotationRepository.create({
      ...dto,
      status: dto.result ? AnnotationStatus.ANNOTATED : AnnotationStatus.PENDING,
    });
    return this.annotationRepository.save(annotation);
  }

  async findAll(type?: AnnotationType): Promise<Annotation[]> {
    const where: any = {};
    if (type) {
      where.type = type;
    }
    return this.annotationRepository.find({
      where,
      order: { createdAt: 'DESC' },
    });
  }

  async findAllForReview(): Promise<Annotation[]> {
    return this.annotationRepository.find({
      where: [{ status: AnnotationStatus.ANNOTATED }, { status: AnnotationStatus.REVIEWED }],
      order: { updatedAt: 'DESC' },
    });
  }

  async findOne(id: number): Promise<Annotation> {
    const annotation = await this.annotationRepository.findOne({ where: { id } });
    if (!annotation) {
      throw new NotFoundException(`标注记录 #${id} 不存在`);
    }
    return annotation;
  }

  async update(id: number, dto: UpdateAnnotationDto): Promise<Annotation> {
    const annotation = await this.findOne(id);
    const shouldUpdateStatus = dto.result && annotation.status === AnnotationStatus.PENDING;
    Object.assign(annotation, dto);
    if (shouldUpdateStatus) {
      annotation.status = AnnotationStatus.ANNOTATED;
    }
    return this.annotationRepository.save(annotation);
  }

  async remove(id: number): Promise<void> {
    const result = await this.annotationRepository.delete(id);
    if (result.affected === 0) {
      throw new NotFoundException(`标注记录 #${id} 不存在`);
    }
  }

  async seedMockData(): Promise<{ text: number; image: number }> {
    const textSamples = [
      { content: '今天天气真好，适合出去走走', result: null },
      { content: '加微信 xxx 免费领取福利，私聊', result: null },
      { content: '正常的商品描述，质量很好', result: null },
      { content: '推荐一个赌博网站，稳赚不赔', result: null },
    ];

    const imageSamples = [
      { imageUrl: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600', content: '风景照片' },
      { imageUrl: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=600', content: '自然风景' },
      { imageUrl: 'https://images.unsplash.com/photo-1519125323398-675f0ddb6308?w=600', content: '产品图片' },
    ];

    let textCount = 0;
    let imageCount = 0;

    for (const sample of textSamples) {
      await this.annotationRepository.save(
        this.annotationRepository.create({
          type: AnnotationType.TEXT,
          content: sample.content,
          status: AnnotationStatus.PENDING,
        }),
      );
      textCount++;
    }

    for (const sample of imageSamples) {
      await this.annotationRepository.save(
        this.annotationRepository.create({
          type: AnnotationType.IMAGE,
          imageUrl: sample.imageUrl,
          content: sample.content,
          status: AnnotationStatus.PENDING,
        }),
      );
      imageCount++;
    }

    return { text: textCount, image: imageCount };
  }
}
